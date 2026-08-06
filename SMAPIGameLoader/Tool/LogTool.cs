using System;
using System.IO;
using System.Threading;

namespace SMAPIGameLoader.Tool;

internal static class LogTool
{
    static readonly string LogFilePath = Path.Combine(FileTool.ExternalFilesDir, "SMAPILoader.log");
    static readonly object LockObj = new object();
    static bool _initialized = false;

    static LogTool()
    {
        try
        {
            // Clear old log on first init
            if (File.Exists(LogFilePath))
                File.Delete(LogFilePath);
            _initialized = true;
        }
        catch { }
    }

    public static void Info(string message) => Write("INFO", message);
    public static void Error(string message) => Write("ERROR", message);
    public static void Error(Exception ex) => Write("ERROR", ex.ToString());
    public static void Debug(string message) => Write("DEBUG", message);

    static void Write(string level, string message)
    {
        string line = $"[{DateTime.Now:yyyy-MM-dd HH:mm:ss}] [{level}] {message}";
        
        // Always write to console (visible in adb logcat)
        Console.WriteLine(line);
        
        // Write to file
        try
        {
            lock (LockObj)
            {
                File.AppendAllText(LogFilePath, line + Environment.NewLine);
            }
        }
        catch { }
    }
}
