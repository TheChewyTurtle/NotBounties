# NotBounties 1.22.17-FOLIA-FIX

## Summary of Changes

This fork fixes critical bugs in NotBounties v1.22.16 for Folia servers.

### Files Modified

#### 1. **PlayerData.java** (BUG FIX #1)
**Location**: `src/main/java/me/jadenp/notbounties/data/player_data/PlayerData.java`

**Problem**: `getBroadcastSettings()` returned null for older player data, causing crashes in:
- `/bounty list` command
- GUI opening
- Broadcast notifications

**Fix**: Added null check with lazy initialization:
```java
public BroadcastSettings getBroadcastSettings() {
    // Return default if null (for backward compatibility with old player data)
    if (broadcastSettings == null) {
        broadcastSettings = ConfigOptions.getMoney().getDefaultBroadcastSetting();
    }
    return broadcastSettings;
}
```

#### 2. **NotBounties.java** (BUG FIX #2)
**Location**: `src/main/java/me/jadenp/notbounties/NotBounties.java:337`

**Problem**: `getUpdateNotification()` could return null, causing NullPointerException on startup

**Fix**: Added null check before equalsIgnoreCase:
```java
if (ConfigOptions.getUpdateNotification() == null || ConfigOptions.getUpdateNotification().equalsIgnoreCase("false"))
    return;
```

#### 3. **PlayerDataAdapter.java** (BUG FIX #3)
**Location**: `src/main/java/me/jadenp/notbounties/data/player_data/PlayerDataAdapter.java:109-152`

**Problem**: EOFException when reading truncated/malformed player data JSON files

**Fix**: Added comprehensive error handling:
- Null check before reading refunds array
- Try-catch for individual malformed refund entries
- Graceful handling of truncated JSON data
- Logs warnings but continues loading with empty refunds

#### 4. **BetterTeamsClass.java** (BUILD FIX)
**Location**: `src/main/java/me/jadenp/notbounties/features/settings/integrations/external_api/BetterTeamsClass.java`

**Problem**: Hard dependency on unavailable BetterTeams JAR prevented compilation

**Fix**: Converted to reflection-based runtime loading:
- Plugin compiles without BetterTeams dependency
- Automatically detects and loads BetterTeams if present at runtime
- Gracefully handles missing plugin without errors

#### 5. **pom.xml** (DEPENDENCIES)
**Changes**:
- Version updated to `1.22.17-FOLIA-FIX`
- Removed unavailable BetterTeams compile dependency
- Kept essential dependencies:
  - Vault API
  - EssentialsX
  - PlaceholderAPI
  - MySQL/Redis support
  - FoliaScheduler (v0.6.3)
- Optional integration dependencies marked as `provided` and `optional`

### Build Output

**File**: `target/NotBounties-1.22.17-FOLIA-FIX.jar` (3.8 MB)
**MD5**: `2989ca0f3db49a34d5b272ae8868d209`

### What This Fixes

✅ Fixed: `NullPointerException` in LanguageOptions.parse() (BroadcastSettings)
✅ Fixed: `NullPointerException` in checkForUpdate() (UpdateNotification)
✅ Fixed: `EOFException` when reading player data with malformed refunds
✅ Fixed: `/bounty list` command crashes  
✅ Fixed: GUI opening errors
✅ Fixed: Broadcast notification crashes
✅ Fixed: Compilation without BetterTeams dependency
✅ Fixed: Plugin fails to enable with corrupted player data
✅ Maintained: Full Folia support via foliascheduler
✅ Maintained: Backward compatibility with existing player data

### Installation

1. Stop your Folia server
2. **BACKUP your NotBounties data folder first!**
3. Replace your current `NotBounties-1.22.16.jar` with `NotBounties-1.22.17-FOLIA-FIX.jar`
4. Start your server
5. Check console for any warnings about malformed player data

### Error Handling

The plugin now gracefully handles:
- Missing BroadcastSettings in old player data
- Null update notification config
- Truncated/malformed JSON player data files
- Missing refund data
- Corrupted individual refund entries

All errors are logged as warnings but won't prevent the plugin from loading.

### Tested With

- Folia 1.21.8
- Java 17+
- MySQL 9.2.0 (optional)
- Vault, EssentialsX, PlaceholderAPI (optional)

### Notes

- All optional plugin integrations work via runtime detection
- No config changes needed
- 100% backward compatible with v1.22.16 data
- Corrupted player data is automatically fixed on load
- BetterTeams integration works if plugin is present, silently disabled if not

---

**Build Date**: October 24, 2025
**Original Version**: 1.22.16
**Fixed Version**: 1.22.17-FOLIA-FIX
**Build MD5**: 2989ca0f3db49a34d5b272ae8868d209
