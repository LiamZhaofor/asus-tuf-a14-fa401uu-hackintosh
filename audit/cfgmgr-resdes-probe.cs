// Exhaustive read-only probe of the CM_Get_Next_Res_Des "first descriptor" contract.
// Tests both 32-bit (ULONG) and zero-initialised pointer-sized handle declarations, and
// every ForType value from 0x00 to 0x40, so the limitation is stated from measurement.
//
// USAGE:  cfgmgr-resdes-probe.exe <instance-ids.txt>
//   One PnP instance id per line, e.g.
//       PCI\VEN_1022&DEV_14EF&SUBSYS_14531022&REV_00\<local-instance-hash>
//   Instance ids carry a per-machine hash component, so they are NOT shipped with this
//   repository - generate the list locally (see audit/README.md).
using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;

static class Brute
{
    const string CFG = "cfgmgr32.dll";

    [DllImport(CFG, CharSet = CharSet.Unicode)]
    static extern int CM_Locate_DevNodeW(out uint pdnDevInst, string pDeviceID, uint ulFlags);
    // 32-bit handle declarations (cfgmgr32.h: LOG_CONF / RES_DES are ULONG)
    [DllImport(CFG)]
    static extern int CM_Get_First_Log_Conf(out uint pLogConf, uint dnDevInst, uint ulFlags);
    [DllImport(CFG)]
    static extern int CM_Get_Next_Res_Des(out uint prdResDes, uint rdResDes, uint ForType, out uint pResType);
    // pointer-sized handle declarations, storage explicitly zeroed before the call
    [DllImport(CFG, EntryPoint = "CM_Get_First_Log_Conf")]
    static extern int CM_Get_First_Log_Conf64(ref IntPtr pLogConf, uint dnDevInst, uint ulFlags);
    [DllImport(CFG, EntryPoint = "CM_Get_Next_Res_Des")]
    static extern int CM_Get_Next_Res_Des64(ref IntPtr prdResDes, IntPtr rdResDes, uint ForType, out uint pResType);

    static void Main(string[] args)
    {
        if (args.Length < 1)
        {
            Console.WriteLine("usage: cfgmgr-resdes-probe.exe <instance-ids.txt>");
            return;
        }
        string[] ids = File.ReadAllLines(args[0]);
        uint[] confs = { 0, 2, 3 };
        string[] cname = { "BASIC", "ALLOC", "BOOT" };
        Console.WriteLine("x64=" + Environment.Is64BitProcess);

        foreach (string iid in ids)
        {
            uint dev;
            int cr = CM_Locate_DevNodeW(out dev, iid, 0);
            Console.WriteLine("\n=== {0}  locate cr={1} devinst=0x{2:X}", iid, cr, dev);
            for (int ci = 0; ci < confs.Length; ci++)
            {
                uint lc32;
                int f32 = CM_Get_First_Log_Conf(out lc32, dev, confs[ci]);
                IntPtr lc64 = IntPtr.Zero;
                int f64 = CM_Get_First_Log_Conf64(ref lc64, dev, confs[ci]);
                Console.WriteLine("  {0}: CM_Get_First_Log_Conf cr32={1} handle32=0x{2:X8} | cr64={3} handle64=0x{4:X}",
                    cname[ci], f32, lc32, f64, (ulong)lc64);
                if (f32 != 0) continue;

                // 32-bit declaration, sweep ForType
                StringBuilder sb = new StringBuilder();
                for (uint ft = 0x00; ft <= 0x41; ft++)
                {
                    uint rd, rt;
                    int c = CM_Get_Next_Res_Des(out rd, lc32, ft, out rt);
                    if (c == 0) sb.AppendFormat(" ForType=0x{0:X2} -> CR_SUCCESS rd=0x{1:X8} type=0x{2:X}", ft, rd, rt);
                }
                Console.WriteLine("    32-bit decl, ForType 0x00..0x41: {0}",
                    sb.Length == 0 ? "CR_SUCCESS never returned (all attempted values failed)" : sb.ToString());

                // pointer-sized declaration, zero-initialised
                IntPtr rd64 = IntPtr.Zero; uint rt64;
                int c64 = CM_Get_Next_Res_Des64(ref rd64, lc64, 0x00, out rt64);
                Console.WriteLine("    64-bit decl (zero-init), ForType=0x00: cr={0} rd=0x{1:X}", c64, (ulong)rd64);
                IntPtr rd64b = IntPtr.Zero; uint rt64b;
                int c64b = CM_Get_Next_Res_Des64(ref rd64b, IntPtr.Zero, 0x00, out rt64b);
                Console.WriteLine("    64-bit decl, rdResDes=NULL:          cr={0}", c64b);
                uint rd32n, rt32n;
                int c32n = CM_Get_Next_Res_Des(out rd32n, 0, 0x00, out rt32n);
                Console.WriteLine("    32-bit decl, rdResDes=NULL:          cr={0}", c32n);
            }
        }
    }
}
