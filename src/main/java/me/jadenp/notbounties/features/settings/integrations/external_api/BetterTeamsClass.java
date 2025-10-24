package me.jadenp.notbounties.features.settings.integrations.external_api;

import org.bukkit.Bukkit;
import org.bukkit.entity.Player;

public class BetterTeamsClass {
    private Object teamPlugin;

    public BetterTeamsClass(){
        try {
            // Try to load BetterTeams at runtime if it's available
            Class<?> teamClass = Class.forName("com.booksaw.betterTeams.Team");
            teamPlugin = teamClass;
        } catch (ClassNotFoundException e) {
            Bukkit.getLogger().warning("[NotBounties] BetterTeams not found - team integration disabled");
        }
    }

    public boolean onSameTeam(Player player1, Player player2) {
        if (teamPlugin == null) return false;
        try {
            Class<?> teamClass = (Class<?>) teamPlugin;
            Object team1 = teamClass.getMethod("getTeam", Player.class).invoke(null, player1);
            Object team2 = teamClass.getMethod("getTeam", Player.class).invoke(null, player2);
            return team1 != null && team2 != null && team1.equals(team2);
        } catch (Exception e) {
            return false;
        }
    }

    public boolean areAllies(Player player1, Player player2) {
        if (teamPlugin == null) return false;
        try {
            Class<?> teamClass = (Class<?>) teamPlugin;
            Object team1 = teamClass.getMethod("getTeam", Player.class).invoke(null, player1);
            Object team2 = teamClass.getMethod("getTeam", Player.class).invoke(null, player2);
            if (team1 == null || team2 == null) return false;
            String team2ID = (String) team2.getClass().getMethod("getID").invoke(team2);
            return (boolean) team1.getClass().getMethod("isAlly", String.class).invoke(team1, team2ID);
        } catch (Exception e) {
            return false;
        }
    }
}
