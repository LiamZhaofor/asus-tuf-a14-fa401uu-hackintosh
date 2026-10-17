// Read-only CfgMgr32 logical-configuration probe (native x64).
//
// DEFECTS THIS FILE FIXES (both were in the previous version of this probe, not in Windows):
//
//  1. SIGNATURE. The real prototype has FIVE parameters:
//         CONFIGRET CM_Get_Next_Res_Des(PRES_DES prdResDes, RES_DES rdResDes,
//                                       RESOURCEID ForType, PULONG pResType, ULONG ulFlags);
//     The old code declared four and omitted `ulFlags`, so the callee read garbage and every
//     call returned CR_INVALID_FLAG (4). With ulFlags = 0 the calls succeed.
//
//  2. RESOURCEID VALUES. `ForType` and the value written to `*pResType` are **RESOURCEID**
//     values, NOT CM_RESOURCE_TYPE values. Calibrated on this machine by sweeping every
//     candidate and matching the returned bytes against an independent decode:
//         ResType_Mem = 0x01   ResType_IO = 0x02   ResType_DMA = 0x03   ResType_IRQ = 0x04
//         ResType_BusNumber = 0x06   ResType_MemLarge = 0x07   0x8001 = device-private
//     Note this differs from CM_RESOURCE_TYPE (Port=1, Interrupt=2, Memory=3, BusNumber=6,
//     MemoryLarge=7): the memory/IO numbers are shifted. The old code searched 0x20 for
//     "BusNumber" - the correct value is 0x06 - which is why it found nothing.
//
// Handle types: cfgmgr32.h declares LOG_CONF and RES_DES as ULONG (32-bit).
//
// Handle management: the LOG_CONF handle is passed as the "previous descriptor" for the FIRST
// CM_Get_Next_Res_Des call; each returned RES_DES handle is released with
// CM_Free_Res_Des_Handle; the LOG_CONF handle is released last with CM_Free_Log_Conf_Handle.
// No CM_Modify_Res_Des / CM_Add_Res_Des / CM_Add_Empty_Log_Conf / CM_Free_Res_Des /
// CM_Free_Log_Conf call is used anywhere: read-only.
//
// The field layout inside the returned bytes is NOT decoded here on purpose - the
// authoritative structural decoder in this repository is audit/pci-logconf-audit.py, which
// reads the same descriptors from the registry. This probe's job is to enumerate and dump.
//
// USAGE:  cfgmgr-resdes-probe.exe <instance-ids.txt> [out.txt]
using System;
using System.Collections.Generic;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;

static class Probe
{
    const string CFG = "cfgmgr32.dll";

    [DllImport(CFG, CharSet = CharSet.Unicode)]
    static extern int CM_Locate_DevNodeW(out uint pdnDevInst, string pDeviceID, uint ulFlags);
    [DllImport(CFG)]
    static extern int CM_Get_First_Log_Conf(out uint pLogConf, uint dnDevInst, uint ulFlags);
    [DllImport(CFG)]
    static extern int CM_Get_Next_Log_Conf(out uint pLogConf, uint hLogConf);
    [DllImport(CFG)]
    static extern int CM_Get_Next_Res_Des(out uint prdResDes, uint rdResDes, uint ForType,
                                          out uint pResType, uint ulFlags);
    [DllImport(CFG)]
    static extern int CM_Get_Res_Des_Data_Size(out uint pulSize, uint rdResDes, uint ulFlags);
    [DllImport(CFG)]
    static extern int CM_Get_Res_Des_Data(uint rdResDes, byte[] Buffer, uint BufferLen, uint ulFlags);
    [DllImport(CFG)]
    static extern int CM_Free_Res_Des_Handle(uint rdResDes);
    [DllImport(CFG)]
    static extern int CM_Free_Log_Conf_Handle(uint lcLogConf);

    const uint BASIC_LOG_CONF = 0;
    const uint ALLOC_LOG_CONF = 2;
    const uint BOOT_LOG_CONF = 3;

    // RESOURCEID values, calibrated (see header)
    const uint ResType_All = 0x00;
    const uint ResType_Mem = 0x01;
    const uint ResType_IO = 0x02;
    const uint ResType_DMA = 0x03;
    const uint ResType_IRQ = 0x04;
    const uint ResType_BusNumber = 0x06;
    const uint ResType_MemLarge = 0x07;

    static readonly uint[] SWEEP = { ResType_All, ResType_Mem, ResType_IO, ResType_DMA, ResType_IRQ,
                                     ResType_BusNumber, ResType_MemLarge };
    static readonly string[] SWEEP_NAME = { "All", "Mem(0x01)", "IO(0x02)", "DMA(0x03)", "IRQ(0x04)",
                                            "BusNumber(0x06)", "MemLarge(0x07)" };

    static string Hex(byte[] b)
    {
        var sb = new StringBuilder(b.Length * 2);
        foreach (byte x in b) sb.Append(x.ToString("x2"));
        return sb.ToString();
    }

    /// Enumerate one logical configuration for one RESOURCEID; release every handle.
    static int Walk(uint logConf, uint forType, List<string> dump)
    {
        uint prev = logConf;
        int n = 0;
        while (true)
        {
            uint cur, rt;
            int cr = CM_Get_Next_Res_Des(out cur, prev, forType, out rt, 0);
            if (cr != 0)
            {
                if (cr != 15) dump.Add("    !! terminated cr=" + cr);
                break;
            }
            n++;
            uint size = 0;
            if (CM_Get_Res_Des_Data_Size(out size, cur, 0) == 0 && size > 0)
            {
                var buf = new byte[size];
                if (CM_Get_Res_Des_Data(cur, buf, size, 0) == 0)
                    dump.Add(string.Format("    [{0}] ResType=0x{1:X4} size={2} hex={3}",
                                           n, rt, size, Hex(buf)));
                else dump.Add("    [" + n + "] ResType=0x" + rt.ToString("X4") + " DATA_FAILED");
            }
            else dump.Add("    [" + n + "] ResType=0x" + rt.ToString("X4") + " SIZE_FAILED");
            if (prev != logConf) CM_Free_Res_Des_Handle(prev);
            prev = cur;
        }
        if (prev != logConf) CM_Free_Res_Des_Handle(prev);
        return n;
    }

    static void Main(string[] args)
    {
        if (args.Length < 1)
        {
            Console.WriteLine("usage: cfgmgr-resdes-probe.exe <instance-ids.txt> [out.txt]");
            return;
        }
        string outPath = args.Length > 1 ? args[1] : null;
        StreamWriter sw = outPath != null ? new StreamWriter(outPath, false, new UTF8Encoding(false)) : null;
        Action<string> W = s => { Console.WriteLine(s); if (sw != null) sw.WriteLine(s); };

        W("# cfgmgr32 read-only logical-configuration probe");
        W("# CM_Get_Next_Res_Des(..., RESOURCEID ForType, PULONG pResType, ULONG ulFlags=0)");
        W("# x64=" + Environment.Is64BitProcess + "  os=" + Environment.OSVersion.VersionString);
        W("# ForType/pResType use RESOURCEID: Mem=0x01 IO=0x02 DMA=0x03 IRQ=0x04 "
          + "BusNumber=0x06 MemLarge=0x07 (device-private shows as 0x8001)");

        uint[] confs = { BASIC_LOG_CONF, ALLOC_LOG_CONF, BOOT_LOG_CONF };
        string[] names = { "BASIC", "ALLOC", "BOOT" };

        foreach (string raw in File.ReadAllLines(args[0]))
        {
            string iid = raw.Trim();
            if (iid.Length == 0 || iid.StartsWith("#")) continue;
            uint dev;
            int cr = CM_Locate_DevNodeW(out dev, iid, 0);
            W("");
            W("=== " + iid);
            W("  locate cr=" + cr + " devinst=0x" + dev.ToString("X"));
            if (cr != 0) continue;

            for (int ci = 0; ci < confs.Length; ci++)
            {
                uint lc;
                int fcr = CM_Get_First_Log_Conf(out lc, dev, confs[ci]);
                if (fcr != 0)
                {
                    W("  " + names[ci] + ": CM_Get_First_Log_Conf cr=" + fcr
                      + (fcr == 14 ? " (CR_NO_MORE_LOG_CONF)" : ""));
                    continue;
                }
                int idx = 0;
                while (true)
                {
                    idx++;
                    W("  " + names[ci] + " logConf#" + idx + " handle=0x" + lc.ToString("X8"));
                    var dump = new List<string>();
                    int total = Walk(lc, ResType_All, dump);
                    W("    total descriptors = " + total);
                    foreach (string s in dump) W(s);

                    var counts = new List<string>();
                    for (int k = 0; k < SWEEP.Length; k++)
                    {
                        if (SWEEP[k] == ResType_All) continue;
                        var scratch = new List<string>();
                        counts.Add(SWEEP_NAME[k] + "=" + Walk(lc, SWEEP[k], scratch));
                    }
                    W("    counts by RESOURCEID: " + string.Join(" ", counts));

                    uint nlc;
                    int ncr = CM_Get_Next_Log_Conf(out nlc, lc);
                    CM_Free_Log_Conf_Handle(lc);
                    if (ncr != 0) break;
                    lc = nlc;
                }
            }
        }
        if (sw != null) { sw.Close(); Console.WriteLine("wrote " + outPath); }
    }
}
