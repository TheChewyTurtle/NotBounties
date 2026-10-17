package me.jadenp.notbounties;

import me.jadenp.notbounties.data.Bounty;
import me.jadenp.notbounties.features.ConfigOptions;
import me.jadenp.notbounties.features.LanguageOptions;
import me.jadenp.notbounties.ui.Commands;
import me.jadenp.notbounties.ui.gui.GUI;
import me.jadenp.notbounties.ui.gui.GUIOptions;
import me.jadenp.notbounties.utils.BountyManager;
import me.jadenp.notbounties.utils.DataManager;
import net.md_5.bungee.api.chat.BaseComponent;
import org.bukkit.Bukkit;
import org.bukkit.OfflinePlayer;
import org.bukkit.command.CommandSender;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.mockito.ArgumentCaptor;
import org.mockito.MockedStatic;

import java.util.ArrayList;
import java.util.AbstractList;
import java.util.List;
import java.util.UUID;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class BountyPaginationRegressionTest {
    private MockedStatic<GUI> gui;
    private MockedStatic<ConfigOptions> config;
    private MockedStatic<LanguageOptions> language;
    private MockedStatic<DataManager> data;
    private MockedStatic<Bukkit> bukkit;
    private CommandSender sender;
    private CommandSender.Spigot spigot;

    @BeforeEach
    void setup() {
        gui = mockStatic(GUI.class);
        config = mockStatic(ConfigOptions.class);
        language = mockStatic(LanguageOptions.class);
        data = mockStatic(DataManager.class);
        bukkit = mockStatic(Bukkit.class);
        GUIOptions options = mock(GUIOptions.class);
        when(options.getName()).thenReturn("Test Bounties");
        when(options.isAddPage()).thenReturn(true);
        when(options.getSortType()).thenReturn(1);
        gui.when(() -> GUI.getGUI("bounty-gui")).thenReturn(options);
        config.when(ConfigOptions::getPluginBountyCommands).thenReturn(List.of("notbounties"));
        language.when(() -> LanguageOptions.getMessage("list-total")).thenReturn("row");
        language.when(() -> LanguageOptions.parse(eq("row"), anyDouble(), any(OfflinePlayer.class)))
                .thenAnswer(call -> "row:" + ((Double) call.getArgument(1)).intValue());
        language.when(LanguageOptions::getPrefix).thenReturn("NB ");
        language.when(() -> LanguageOptions.getMessage("no-permission")).thenReturn("no-permission");
        language.when(() -> LanguageOptions.parse(anyString(), nullable(OfflinePlayer.class)))
                .thenAnswer(call -> call.getArgument(0));
        bukkit.when(() -> Bukkit.getOfflinePlayer(any(UUID.class))).thenReturn(mock(OfflinePlayer.class));
        sender = mock(CommandSender.class);
        spigot = mock(CommandSender.Spigot.class);
        when(sender.spigot()).thenReturn(spigot);
        when(sender.hasPermission(anyString())).thenReturn(true);
        data.when(() -> DataManager.getAllBounties(1)).thenReturn(List.of());
    }

    @AfterEach
    void close() {
        Stream.of(bukkit, data, language, config, gui).filter(java.util.Objects::nonNull)
                .forEach(MockedStatic::close);
    }

    @ParameterizedTest
    @ValueSource(strings = {"0", "-1", "-2147483648", "2147483648", "9223372036854775807", "not-a-number"})
    void invalidOneBasedCommandPagesFailBeforeListing(String page) {
        assertFalse(new Commands().executeCommand(sender, new String[]{"list", page}, false));
        verify(sender).sendMessage("Page number must be a positive integer.");
        data.verifyNoInteractions();
        verifyNoInteractions(spigot);
    }

    @ParameterizedTest
    @ValueSource(ints = {-1, Integer.MIN_VALUE})
    void publicListingAlsoRejectsNegativeZeroBasedPages(int page) {
        BountyManager.listBounties(sender, page);
        verify(sender).sendMessage("Page number must be a positive integer.");
        data.verifyNoInteractions();
        verifyNoInteractions(spigot);
    }

    @ParameterizedTest
    @ValueSource(ints = {0, 1, 10, 11})
    void validFirstPagesKeepRowsAndNavigation(int size) {
        useBounties(size);
        assertTrue(new Commands().executeCommand(sender, new String[]{"list", "1"}, false));
        assertEquals(Math.min(size, 10), renderedRows().size());
        verify(sender).sendMessage(contains("Test Bounties 1"));
        List<String> links = footerLinks();
        assertEquals(size > 10 ? List.of("/notbounties list 2") : List.of(), links);
    }

    @Test
    void secondPageKeepsItsExactSliceAndPreviousNextTargets() {
        useBounties(35);
        BountyManager.listBounties(sender, 1);
        assertEquals(List.of("row:11", "row:12", "row:13", "row:14", "row:15", "row:16", "row:17", "row:18", "row:19", "row:20"), renderedRows());
        assertEquals(List.of("/notbounties list 1", "/notbounties list 3"), footerLinks());
    }

    @Test
    void partialLastPageContainsOnlyRemainingRows() {
        useBounties(11);
        BountyManager.listBounties(sender, 1);
        assertEquals(List.of("row:11"), renderedRows());
        assertEquals(List.of("/notbounties list 1"), footerLinks());
    }

    @ParameterizedTest
    @ValueSource(ints = {2, 214748364, 2147483646, Integer.MAX_VALUE})
    void outOfRangeOrOverflowSizedPagesNeverIndexRows(int page) {
        useBounties(11);
        BountyManager.listBounties(sender, page);
        verify(sender).sendMessage("Page number must be between 1 and 2.");
        verifyNoInteractions(spigot);
    }

    @Test
    void maximumIntegerCommandPageIsRejectedByRangeWithoutMultiplicationOverflow() {
        useBounties(1);
        assertTrue(new Commands().executeCommand(sender, new String[]{"list", "2147483647"}, false));
        verify(sender).sendMessage("Page number must be between 1 and 1.");
        verifyNoInteractions(spigot);
    }

    @Test
    void finalPageOfMaximumSizedVirtualListDoesNotOverflowItsEndIndex() {
        Bounty row = mock(Bounty.class);
        when(row.getUUID()).thenReturn(UUID.randomUUID());
        when(row.getTotalDisplayBounty()).thenReturn(1D);
        List<Integer> visited = new ArrayList<>();
        List<Bounty> virtual = new AbstractList<>() {
            @Override public Bounty get(int index) {
                if (index < 0 || index >= size()) throw new IndexOutOfBoundsException(index);
                visited.add(index);
                return row;
            }
            @Override public int size() { return Integer.MAX_VALUE; }
        };
        data.when(() -> DataManager.getAllBounties(1)).thenReturn(virtual);
        BountyManager.listBounties(sender, 214748364);
        assertEquals(List.of(2147483640, 2147483641, 2147483642, 2147483643,
                2147483644, 2147483645, 2147483646), visited.stream().distinct().toList());
        assertEquals(7, renderedRows().size());
        assertEquals(List.of("/notbounties list 214748364"), footerLinks());
    }

    @Test
    void viewPermissionDenialStillPrecedesAnyBountyLookup() {
        when(sender.hasPermission("notbounties.view")).thenReturn(false);
        assertFalse(new Commands().executeCommand(sender, new String[]{"list", "1"}, false));
        verify(sender).sendMessage("NB no-permission");
        data.verifyNoInteractions();
        verifyNoInteractions(spigot);
    }

    private void useBounties(int size) {
        List<Bounty> bounties = new ArrayList<>();
        for (int index = 0; index < size; index++) {
            Bounty bounty = mock(Bounty.class);
            when(bounty.getUUID()).thenReturn(new UUID(0, index + 1));
            when(bounty.getTotalDisplayBounty()).thenReturn((double) index + 1);
            bounties.add(bounty);
        }
        data.when(() -> DataManager.getAllBounties(1)).thenReturn(bounties);
    }

    private List<String> renderedRows() {
        ArgumentCaptor<String> messages = ArgumentCaptor.forClass(String.class);
        verify(sender, atLeastOnce()).sendMessage(messages.capture());
        return messages.getAllValues().stream().filter(message -> message.startsWith("row:")).toList();
    }

    private List<String> footerLinks() {
        ArgumentCaptor<BaseComponent> footer = ArgumentCaptor.forClass(BaseComponent.class);
        verify(spigot).sendMessage(footer.capture());
        List<String> links = new ArrayList<>();
        collectLinks(footer.getValue(), links);
        return links;
    }

    private void collectLinks(BaseComponent component, List<String> links) {
        if (component.getClickEvent() != null) links.add(component.getClickEvent().getValue());
        if (component.getExtra() != null) component.getExtra().forEach(child -> collectLinks(child, links));
    }
}
