using Android.App;
using Android.Content.PM;
using Android.OS;
using System;
using System.Linq;

namespace SMAPIGameLoader;

internal static class StardewApkTool
{
    public static readonly string[] KnownPackageNames = new[]
    {
        "com.chucklefish.stardewvalley",
        "com.chucklefish.stardewvalleysamsung",
        "com.zane.stardewvalley",
    };

    static PackageInfo? _currentPackageInfo;
    static string? _detectedPackageName;

    static StardewApkTool()
    {
        Console.WriteLine("Initialize Stardew Apk Tool");
        
        foreach (var pkg in KnownPackageNames)
        {
            var info = ApkTool.GetPackageInfo(pkg);
            if (info != null)
            {
                _currentPackageInfo = info;
                _detectedPackageName = pkg;
                Console.WriteLine($"Game found: {pkg}");
                return;
            }
        }

        // Fallback: scan all installed packages
        try
        {
            var pm = Application.Context.PackageManager;
            var apps = pm.GetInstalledApplications(PackageInfoFlags.MatchAll);
            foreach (var app in apps)
            {
                if (app.PackageName?.Contains("stardew", StringComparison.OrdinalIgnoreCase) == true)
                {
                    var info = ApkTool.GetPackageInfo(app.PackageName);
                    if (info != null)
                    {
                        _currentPackageInfo = info;
                        _detectedPackageName = app.PackageName;
                        Console.WriteLine($"Game found via scan: {app.PackageName}");
                        return;
                    }
                }
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine("Scan fallback failed: " + ex.Message);
        }

        Console.WriteLine("Stardew Valley not found on device");
    }

    public static PackageInfo? CurrentPackageInfo => _currentPackageInfo;
    public static bool IsInstalled => CurrentPackageInfo != null;
    public static string? DetectedPackageName => _detectedPackageName;

    public static Android.Content.Context GetContext => Application.Context;
    
    // CHANGED: Use SourceDir instead of PublicSourceDir for better compatibility
    public static string? BaseApkPath => CurrentPackageInfo?.ApplicationInfo?.SourceDir;
    
    public static string? Arm64ApkPath
    {
        get
        {
            try
            {
                if (CurrentPackageInfo == null) return null;

                var splitDirs = CurrentPackageInfo.ApplicationInfo?.SplitSourceDirs;
                if (splitDirs != null && splitDirs.Length > 0)
                {
                    var arm64 = splitDirs.FirstOrDefault(path => 
                        path.Contains("split_config.arm64", StringComparison.OrdinalIgnoreCase));
                    if (arm64 != null) return arm64;
                }
                
                // Single APK fallback
                return BaseApkPath;
            }
            catch (Exception ex)
            {
                ErrorDialogTool.Show(ex, "Error getting Arm64ApkPath");
                return null;
            }
        }
    }

    public static string? ContentApkPath
    {
        get
        {
            try
            {
                if (CurrentPackageInfo == null) return null;

                var splitDirs = CurrentPackageInfo.ApplicationInfo?.SplitSourceDirs;
                if (splitDirs != null && splitDirs.Length > 0)
                {
                    var content = splitDirs.FirstOrDefault(path => 
                        path.Contains("split_content", StringComparison.OrdinalIgnoreCase));
                    if (content != null) return content;
                }
                
                // Single APK fallback
                return BaseApkPath;
            }
            catch (Exception ex)
            {
                ErrorDialogTool.Show(ex, "Error getting ContentApkPath");
                return null;
            }
        }
    }

    public static Version? GameVersionSupport => new Version(1, 6, 15, 3);

    public static Version CurrentGameVersion
    {
        get
        {
            try
            {
                return new Version(CurrentPackageInfo?.VersionName ?? "0.0.0.0");
            }
            catch
            {
                return new Version(0, 0, 0, 0);
            }
        }
    }

    public static bool IsGameVersionSupport => true;
}
