package me.jadenp.notbounties.utils;

import com.ironcladmc.ironorders.api.IronOrdersAPI;
import me.jadenp.notbounties.NotBounties;

/**
 * Helper class for depositing taxes to the Ironclad_Government account via IronOrders.
 * If IronOrders is not available, taxes are simply discarded (default behavior).
 */
public class GovernmentTaxHelper {

    /**
     * Deposit bounty placement tax to the government account.
     * This is called when a player places a bounty and pays the tax.
     *
     * @param taxAmount the tax amount collected
     */
    public static void depositBountyTax(double taxAmount) {
        if (taxAmount <= 0) return;

        try {
            if (IronOrdersAPI.isAvailable()) {
                IronOrdersAPI.depositToGovernment(taxAmount, "NotBounties", "Bounty placement tax")
                        .thenAccept(newBalance -> {
                            if (newBalance >= 0) {
                                NotBounties.debugMessage("Deposited $" + String.format("%.2f", taxAmount) +
                                        " bounty tax to Government. New balance: $" + String.format("%.2f", newBalance), false);
                            }
                        });
            }
        } catch (NoClassDefFoundError e) {
            // IronOrders not installed, silently ignore
        }
    }

    /**
     * Deposit death tax to the government account.
     * This is called when a bounty is claimed and the victim pays the death tax.
     *
     * @param taxAmount the death tax amount collected
     */
    public static void depositDeathTax(double taxAmount) {
        if (taxAmount <= 0) return;

        try {
            if (IronOrdersAPI.isAvailable()) {
                IronOrdersAPI.depositToGovernment(taxAmount, "NotBounties", "Bounty death tax")
                        .thenAccept(newBalance -> {
                            if (newBalance >= 0) {
                                NotBounties.debugMessage("Deposited $" + String.format("%.2f", taxAmount) +
                                        " death tax to Government. New balance: $" + String.format("%.2f", newBalance), false);
                            }
                        });
            }
        } catch (NoClassDefFoundError e) {
            // IronOrders not installed, silently ignore
        }
    }

    /**
     * Check if IronOrders government system is available.
     * @return true if taxes can be deposited to the government
     */
    public static boolean isGovernmentAvailable() {
        try {
            return IronOrdersAPI.isAvailable();
        } catch (NoClassDefFoundError e) {
            return false;
        }
    }
}
