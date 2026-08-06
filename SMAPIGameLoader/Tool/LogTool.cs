using System;
using System.IO;

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

        Console.WriteLine(line);

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
