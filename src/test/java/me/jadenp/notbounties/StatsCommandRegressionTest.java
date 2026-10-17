package me.jadenp.notbounties;

import me.jadenp.notbounties.features.LanguageOptions;
import me.jadenp.notbounties.features.settings.money.NumberFormatting;
import me.jadenp.notbounties.ui.Commands;
import me.jadenp.notbounties.utils.DataManager;
import me.jadenp.notbounties.utils.LoggedPlayers;
import org.bukkit.Bukkit;
import org.bukkit.OfflinePlayer;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.Player;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.MockedStatic;

import java.util.UUID;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class StatsCommandRegressionTest {
    private MockedStatic<LanguageOptions> language;
    private MockedStatic<NumberFormatting> numbers;
    private MockedStatic<DataManager> data;
    private MockedStatic<LoggedPlayers> players;
    private MockedStatic<Bukkit> bukkit;
    private final UUID ownerId = UUID.randomUUID();
    private CommandSender console;
    private OfflinePlayer owner;

    @BeforeEach
    void setup() {
        language = mockStatic(LanguageOptions.class);
        numbers = mockStatic(NumberFormatting.class);
        data = mockStatic(DataManager.class);
        players = mockStatic(LoggedPlayers.class);
        bukkit = mockStatic(Bukkit.class);
        language.when(LanguageOptions::getPrefix).thenReturn("NB ");
        language.when(() -> LanguageOptions.getMessage(anyString()))
                .thenAnswer(call -> "{amount} " + call.getArgument(0, String.class));
        language.when(() -> LanguageOptions.parse(anyString(), nullable(OfflinePlayer.class)))
                .thenAnswer(call -> call.getArgument(0));
        language.when(() -> LanguageOptions.parse(anyString(), anyString(), nullable(OfflinePlayer.class)))
                .thenAnswer(call -> call.getArgument(0));
        numbers.when(NumberFormatting::getCurrencyPrefix).thenReturn("$");
        numbers.when(NumberFormatting::getCurrencySuffix).thenReturn("");
        numbers.when(() -> NumberFormatting.formatNumber(100D)).thenReturn("100");
        data.when(() -> DataManager.getStat(any(UUID.class), any(Leaderboard.class))).thenReturn(100D);
        players.when(() -> LoggedPlayers.getPlayer("KnownPlayer")).thenReturn(ownerId);
        owner = mock(OfflinePlayer.class);
        when(owner.getUniqueId()).thenReturn(ownerId);
        bukkit.when(() -> Bukkit.getOfflinePlayer(ownerId)).thenReturn(owner);
        console = mock(CommandSender.class);
        when(console.hasPermission(anyString())).thenReturn(true);
    }

    @AfterEach
    void close() {
        Stream.of(bukkit, players, data, numbers, language).filter(java.util.Objects::nonNull)
                .forEach(MockedStatic::close);
    }

    @Test
    void targetlessConsoleStatReturnsUsageWithoutReadingANullPlayer() {
        assertFalse(new Commands().executeCommand(console, new String[]{"stat"}, false));
        verify(console).sendMessage("Console usage: /notbounties stat <leaderboard> <player>");
        data.verifyNoInteractions();
    }

    @Test
    void typedConsoleStatWithoutTargetAlsoReturnsUsage() {
        assertFalse(new Commands().executeCommand(console, new String[]{"stat", "ALL"}, false));
        verify(console).sendMessage("Console usage: /notbounties stat <leaderboard> <player>");
        data.verifyNoInteractions();
    }

    @Test
    void explicitOfflineTargetStatsAreRenderedToConsoleExactlyOnce() {
        assertTrue(new Commands().executeCommand(console, new String[]{"stat", "ALL", "KnownPlayer"}, false));
        verify(console).sendMessage("NB $100 bounty-stat.all.short");
        verify(console, times(1)).sendMessage(anyString());
        data.verify(() -> DataManager.getStat(ownerId, Leaderboard.ALL));
        verify(owner, never()).getPlayer();
    }

    @Test
    void explicitTargetStatsStillGoToThePlayerWhoRequestedThem() {
        Player requester = mock(Player.class);
        when(requester.hasPermission(anyString())).thenReturn(true);
        assertTrue(new Commands().executeCommand(requester, new String[]{"stat", "ALL", "KnownPlayer"}, false));
        verify(requester).sendMessage("NB $100 bounty-stat.all.short");
        verify(owner, never()).getPlayer();
    }

    @Test
    void selfPlayerStatsRetainTheirLongRenderingAndRecipient() {
        Player self = mock(Player.class);
        when(self.hasPermission(anyString())).thenReturn(true);
        when(self.getUniqueId()).thenReturn(ownerId);
        when(self.isOnline()).thenReturn(true);
        when(self.getPlayer()).thenReturn(self);
        assertTrue(new Commands().executeCommand(self, new String[]{"stat"}, false));
        verify(self).sendMessage("NB $100 bounty-stat.all.long");
    }

    @Test
    void typedSelfPlayerStatsRetainNonMoneyRendering() {
        Player self = mock(Player.class);
        when(self.hasPermission(anyString())).thenReturn(true);
        when(self.getUniqueId()).thenReturn(ownerId);
        when(self.isOnline()).thenReturn(true);
        when(self.getPlayer()).thenReturn(self);
        assertTrue(new Commands().executeCommand(self, new String[]{"stat", "SET"}, false));
        verify(self).sendMessage("NB 100 bounty-stat.set.long");
    }

    @Test
    void statsPermissionDenialStillPrecedesAnyLookupOrRendering() {
        when(console.hasPermission("notbounties.stats")).thenReturn(false);
        assertFalse(new Commands().executeCommand(console, new String[]{"stat", "ALL", "KnownPlayer"}, false));
        verify(console).sendMessage(contains("no-permission"));
        players.verifyNoInteractions();
        data.verifyNoInteractions();
    }

    @Test
    void unknownTargetIsRejectedWithoutReadingOrChangingStats() {
        assertFalse(new Commands().executeCommand(console, new String[]{"stat", "ALL", "UnknownPlayer"}, false));
        verify(console).sendMessage(contains("unknown-player"));
        data.verifyNoInteractions();
    }
}
