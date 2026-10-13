# Round 8 - Windows-side PCI topology and resource audit (read-only)

Sources: `pnputil-all.xml` + `plan.json`

## 1. PCI functions (42)

| BDF | vendor:device | class | problem | parent | ACPI path | windows (merged) |
|---|---|---|---|---|---|---|
| 00:00.0 | VEN_1022&DEV_14E8&SUBSYS_1E431043&REV_00 | System | - | non-pci | ACPI(_SB_)#ACPI(PCI0)#ACPI(D002) | - |
| 00:01.0 | VEN_1022&DEV_14EA&SUBSYS_00000000&REV_00 | System | - | non-pci | ACPI(_SB_)#ACPI(PCI0)#PCI(0100) | - |
| 00:01.1 | VEN_1022&DEV_14ED&SUBSYS_1E431043&REV_00 | System | - | non-pci | ACPI(_SB_)#ACPI(PCI0)#ACPI(GPP0) | 0xDC000000-0xDD0FFFFF, 0x7C00000000-0x7E01FFFFFF |
| 00:02.0 | VEN_1022&DEV_14EA&SUBSYS_00000000&REV_00 | System | - | non-pci | ACPI(_SB_)#ACPI(PCI0)#PCI(0200) | - |
| 00:02.1 | VEN_1022&DEV_14EE&SUBSYS_1E431043&REV_00 | System | - | non-pci | ACPI(_SB_)#ACPI(PCI0)#ACPI(GPP5) | 0xDDF00000-0xDDFFFFFF |
| 00:02.2 | VEN_1022&DEV_14EE&SUBSYS_1E431043&REV_00 | System | - | non-pci | ACPI(_SB_)#ACPI(PCI0)#ACPI(GPP6) | 0xDDB00000-0xDDCFFFFF, 0x7FFFF00000-0x7FFFFFFFFF |
| 00:02.4 | VEN_1022&DEV_14EE&SUBSYS_1E431043&REV_00 | System | - | non-pci | ACPI(_SB_)#ACPI(PCI0)#ACPI(GPP8) | 0xDDE00000-0xDDEFFFFF |
| 00:03.0 | VEN_1022&DEV_14EA&SUBSYS_00000000&REV_00 | System | - | non-pci | ACPI(_SB_)#ACPI(PCI0)#PCI(0300) | - |
| 00:03.1 | VEN_1022&DEV_14EF&SUBSYS_14531022&REV_00 | System | - | non-pci | ACPI(_SB_)#ACPI(PCI0)#ACPI(GP11) | 0xC4000000-0xDBFFFFFF, 0x6C00000000-0x7BFFFFFFFF |
| 00:04.0 | VEN_1022&DEV_14EA&SUBSYS_00000000&REV_00 | System | - | non-pci | ACPI(_SB_)#ACPI(PCI0)#PCI(0400) | - |
| 00:08.0 | VEN_1022&DEV_14EA&SUBSYS_00000000&REV_00 | System | - | non-pci | ACPI(_SB_)#ACPI(PCI0)#PCI(0800) | - |
| 00:08.1 | VEN_1022&DEV_14EB&SUBSYS_14EB1022&REV_00 | System | - | non-pci | ACPI(_SB_)#ACPI(PCI0)#ACPI(GP17) | 0xDD200000-0xDD7FFFFF, 0x7E10000000-0x7E207FFFFF |
| 00:08.2 | VEN_1022&DEV_14EB&SUBSYS_14EB1022&REV_00 | System | - | non-pci | ACPI(_SB_)#ACPI(PCI0)#ACPI(GP18) | 0xDDD00000-0xDDDFFFFF, 0x7E20900000-0x7E209FFFFF |
| 00:08.3 | VEN_1022&DEV_14EB&SUBSYS_14EB1022&REV_00 | System | - | non-pci | ACPI(_SB_)#ACPI(PCI0)#ACPI(GP19) | 0xDD800000-0xDDAFFFFF |
| 00:14.0 | VEN_1022&DEV_790B&SUBSYS_1E431043&REV_71 | System | - | non-pci | ACPI(_SB_)#ACPI(PCI0)#ACPI(D02D) | - |
| 00:14.3 | VEN_1022&DEV_790E&SUBSYS_1E431043&REV_51 | System | - | non-pci | ACPI(_SB_)#ACPI(PCI0)#ACPI(SBRG) | - |
| 00:18.0 | VEN_1022&DEV_14F0&SUBSYS_00000000&REV_00 | System | - | non-pci | ACPI(_SB_)#ACPI(PCI0)#PCI(1800) | - |
| 00:18.1 | VEN_1022&DEV_14F1&SUBSYS_00000000&REV_00 | System | - | non-pci | ACPI(_SB_)#ACPI(PCI0)#PCI(1801) | - |
| 00:18.2 | VEN_1022&DEV_14F2&SUBSYS_00000000&REV_00 | System | - | non-pci | ACPI(_SB_)#ACPI(PCI0)#PCI(1802) | - |
| 00:18.3 | VEN_1022&DEV_14F3&SUBSYS_00000000&REV_00 | System | - | non-pci | ACPI(_SB_)#ACPI(PCI0)#PCI(1803) | - |
| 00:18.4 | VEN_1022&DEV_14F4&SUBSYS_00000000&REV_00 | System | - | non-pci | ACPI(_SB_)#ACPI(PCI0)#PCI(1804) | - |
| 00:18.5 | VEN_1022&DEV_14F5&SUBSYS_00000000&REV_00 | System | - | non-pci | ACPI(_SB_)#ACPI(PCI0)#PCI(1805) | - |
| 00:18.6 | VEN_1022&DEV_14F6&SUBSYS_00000000&REV_00 | System | - | non-pci | ACPI(_SB_)#ACPI(PCI0)#PCI(1806) | - |
| 00:18.7 | VEN_1022&DEV_14F7&SUBSYS_00000000&REV_00 | System | - | non-pci | ACPI(_SB_)#ACPI(PCI0)#PCI(1807) | - |
| 01:00.0 | VEN_10DE&DEV_28E1&SUBSYS_1E431043&REV_A1 | Display | - | 00:01.1 | ACPI(_SB_)#ACPI(PCI0)#ACPI(GPP0)#ACPI(PEGP) | 0xDC000000-0xDCFFFFFF, 0x7C00000000-0x7DFFFFFFFF, 0x7E00000000-0x7E01FFFFFF |
| 01:00.1 | VEN_10DE&DEV_22BE&SUBSYS_1E431043&REV_A1 | System | - | 00:01.1 | ACPI(_SB_)#ACPI(PCI0)#ACPI(GPP0)#ACPI(NHDA) | 0xDD0FC000-0xDD0FFFFF |
| 02:00.0 | VEN_10EC&DEV_525A&SUBSYS_202F1043&REV_01 | MTD | - | 00:02.1 | ACPI(_SB_)#ACPI(PCI0)#ACPI(GPP5)#ACPI(DEV0) | 0xDDFFF000-0xDDFFFFFF |
| 03:00.0 | VEN_14C3&DEV_0616&SUBSYS_E0DF105B&REV_00 | Net | - | 00:02.2 | ACPI(_SB_)#ACPI(PCI0)#ACPI(GPP6)#ACPI(WLAN) | 0xDDCF8000-0xDDCFFFFF, 0x7FFFF00000-0x7FFFFFFFFF |
| 04:00.0 | VEN_15B7&DEV_5017&SUBSYS_501715B7&REV_01 | SCSIAdapter | - | 00:02.4 | ACPI(_SB_)#ACPI(PCI0)#ACPI(GPP8)#ACPI(NVME) | 0xDDE00000-0xDDE03FFF |
| 65:00.0 | VEN_1002&DEV_1900&SUBSYS_1E431043&REV_CC | Display | - | 00:08.1 | ACPI(_SB_)#ACPI(PCI0)#ACPI(GP17)#ACPI(VGA_) | 0xDD200000-0xDD3FFFFF, 0xDD700000-0xDD77FFFF, 0x7E10000000-0x7E1FFFFFFF |
| 65:00.1 | VEN_1002&DEV_1640&SUBSYS_1E431043&REV_00 | System | - | 00:08.1 | ACPI(_SB_)#ACPI(PCI0)#ACPI(GP17)#ACPI(HDAU) | 0xDD7F8000-0xDD7FBFFF |
| 65:00.2 | VEN_1022&DEV_15C7&SUBSYS_1E431043&REV_00 | SecurityDevices | - | 00:08.1 | ACPI(_SB_)#ACPI(PCI0)#ACPI(GP17)#PCI(0002) | 0xDD600000-0xDD6FFFFF, 0xDD7FE000-0xDD7FFFFF |
| 65:00.3 | VEN_1022&DEV_15B9&SUBSYS_201F1043&REV_00 | USB | - | 00:08.1 | ACPI(_SB_)#ACPI(PCI0)#ACPI(GP17)#ACPI(XHC0) | 0xDD500000-0xDD5FFFFF |
| 65:00.4 | VEN_1022&DEV_15BA&SUBSYS_201F1043&REV_00 | USB | - | 00:08.1 | ACPI(_SB_)#ACPI(PCI0)#ACPI(GP17)#ACPI(XHC1) | 0xDD400000-0xDD4FFFFF |
| 65:00.5 | VEN_1022&DEV_15E2&SUBSYS_1E431043&REV_63 | System | - | 00:08.1 | ACPI(_SB_)#ACPI(PCI0)#ACPI(GP17)#ACPI(ACP_) | 0xDD780000-0xDD7BFFFF, 0x7E20000000-0x7E207FFFFF |
| 65:00.6 | VEN_1022&DEV_15E3&SUBSYS_1E431043&REV_00 | System | - | 00:08.1 | ACPI(_SB_)#ACPI(PCI0)#ACPI(GP17)#ACPI(AZAL) | 0xDD7C0000-0xDD7C7FFF |
| 66:00.0 | VEN_1022&DEV_14EC&SUBSYS_1E431043&REV_00 | System | - | 00:08.2 | ACPI(_SB_)#ACPI(PCI0)#ACPI(GP18)#PCI(0000) | - |
| 66:00.1 | VEN_1022&DEV_1502&SUBSYS_20CF1043&REV_00 | ComputeAccelerator | - | 00:08.2 | ACPI(_SB_)#ACPI(PCI0)#ACPI(GP18)#ACPI(NPU_) | 0xDDD3E000-0xDDD3FFFF, 0xDDD40000-0xDDD7FFFF, 0xDDD80000-0xDDDFFFFF, 0x7E209C0000-0x7E209FFFFF |
| 67:00.0 | VEN_1022&DEV_14EC&SUBSYS_1E431043&REV_00 | System | - | 00:08.3 | ACPI(_SB_)#ACPI(PCI0)#ACPI(GP19)#ACPI(XHC2) | - |
| 67:00.3 | VEN_1022&DEV_15C0&SUBSYS_201F1043&REV_00 | USB | - | 00:08.3 | ACPI(_SB_)#ACPI(PCI0)#ACPI(GP19)#ACPI(XHC3) | 0xDD900000-0xDD9FFFFF |
| 67:00.4 | VEN_1022&DEV_15C1&SUBSYS_201F1043&REV_00 | USB | - | 00:08.3 | ACPI(_SB_)#ACPI(PCI0)#ACPI(GP19)#ACPI(XHC4) | 0xDD800000-0xDD8FFFFF |
| 67:00.5 | VEN_1022&DEV_1668&SUBSYS_20AF1043&REV_00 | USB | - | 00:08.3 | ACPI(_SB_)#ACPI(PCI0)#ACPI(GP19)#ACPI(NHI0) | 0xDDA00000-0xDDA7FFFF |

## 2. PCI-to-PCI bridges (8)

### 00:08.1 - VEN_1022&DEV_14EB&SUBSYS_14EB1022&REV_00 (PCI Express 根端口)
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GP17)`
* primary bus (reported) = 0
* secondary / subordinate (**derived from children, not read**) = 101 / 101
* children: 65:00.0, 65:00.1, 65:00.2, 65:00.3, 65:00.4, 65:00.5, 65:00.6
* forwarded memory, CfgMgr32 (authoritative): 0xDD200000-0xDD7FFFFF, 0x7E10000000-0x7E207FFFFF [PREFETCHABLE]
* forwarded memory, pnputil (lossy - drops MemoryLarge): 0xDD200000-0xDD7FFFFF, 0x7E10000000-0x7E207FFFFF
* forwarded IO: E000-EFFF

### 00:08.2 - VEN_1022&DEV_14EB&SUBSYS_14EB1022&REV_00 (PCI Express 根端口)
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GP18)`
* primary bus (reported) = 0
* secondary / subordinate (**derived from children, not read**) = 102 / 102
* children: 66:00.0, 66:00.1
* forwarded memory, CfgMgr32 (authoritative): 0xDDD00000-0xDDDFFFFF, 0x7E20900000-0x7E209FFFFF [PREFETCHABLE]
* forwarded memory, pnputil (lossy - drops MemoryLarge): 0xDDD00000-0xDDDFFFFF, 0x7E20900000-0x7E209FFFFF
* forwarded IO: (none)

### 00:08.3 - VEN_1022&DEV_14EB&SUBSYS_14EB1022&REV_00 (PCI Express 根端口)
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GP19)`
* primary bus (reported) = 0
* secondary / subordinate (**derived from children, not read**) = 103 / 103
* children: 67:00.0, 67:00.3, 67:00.4, 67:00.5
* forwarded memory, CfgMgr32 (authoritative): 0xDD800000-0xDDAFFFFF
* forwarded memory, pnputil (lossy - drops MemoryLarge): 0xDD800000-0xDDAFFFFF
* forwarded IO: (none)

### 00:03.1 - VEN_1022&DEV_14EF&SUBSYS_14531022&REV_00 (PCI Express 根端口)
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GP11)`
* primary bus (reported) = 0
* secondary / subordinate (**derived from children, not read**) = None / None
* children: (none - derived range unknown)
* forwarded memory, CfgMgr32 (authoritative): 0xC4000000-0xDBFFFFFF, 0x6C00000000-0x7BFFFFFFFF [PREFETCHABLE] [MemoryLarge]
* forwarded memory, pnputil (lossy - drops MemoryLarge): 0xC4000000-0xDBFFFFFF
* forwarded IO: A000-DFFF

### 00:02.1 - VEN_1022&DEV_14EE&SUBSYS_1E431043&REV_00 (PCI Express 根端口)
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GPP5)`
* primary bus (reported) = 0
* secondary / subordinate (**derived from children, not read**) = 2 / 2
* children: 02:00.0
* forwarded memory, CfgMgr32 (authoritative): 0xDDF00000-0xDDFFFFFF
* forwarded memory, pnputil (lossy - drops MemoryLarge): 0xDDF00000-0xDDFFFFFF
* forwarded IO: (none)

### 00:02.2 - VEN_1022&DEV_14EE&SUBSYS_1E431043&REV_00 (PCI Express 根端口)
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GPP6)`
* primary bus (reported) = 0
* secondary / subordinate (**derived from children, not read**) = 3 / 3
* children: 03:00.0
* forwarded memory, CfgMgr32 (authoritative): 0xDDB00000-0xDDCFFFFF, 0x7FFFF00000-0x7FFFFFFFFF [PREFETCHABLE]
* forwarded memory, pnputil (lossy - drops MemoryLarge): 0xDDB00000-0xDDCFFFFF, 0x7FFFF00000-0x7FFFFFFFFF
* forwarded IO: (none)

### 00:02.4 - VEN_1022&DEV_14EE&SUBSYS_1E431043&REV_00 (PCI Express 根端口)
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GPP8)`
* primary bus (reported) = 0
* secondary / subordinate (**derived from children, not read**) = 4 / 4
* children: 04:00.0
* forwarded memory, CfgMgr32 (authoritative): 0xDDE00000-0xDDEFFFFF
* forwarded memory, pnputil (lossy - drops MemoryLarge): 0xDDE00000-0xDDEFFFFF
* forwarded IO: (none)

### 00:01.1 - VEN_1022&DEV_14ED&SUBSYS_1E431043&REV_00 (PCI Express 根端口)
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GPP0)`
* primary bus (reported) = 0
* secondary / subordinate (**derived from children, not read**) = 1 / 1
* children: 01:00.0, 01:00.1
* forwarded memory, CfgMgr32 (authoritative): 0xDC000000-0xDD0FFFFF, 0x7C00000000-0x7E01FFFFFF [PREFETCHABLE] [MemoryLarge]
* forwarded memory, pnputil (lossy - drops MemoryLarge): 0xDC000000-0xDD0FFFFF
* forwarded IO: F000-FFFF

## 3. Source comparison - pnputil vs CfgMgr32

* devices whose window set differs: **3**
  * `00:01.1` only_in_cfgmgr=[['0x7C00000000', '0x7E01FFFFFF']] only_in_pnputil=[]
  * `00:03.1` only_in_cfgmgr=[['0x6C00000000', '0x7BFFFFFFFF']] only_in_pnputil=[]
  * `01:00.0` only_in_cfgmgr=[['0x7C00000000', '0x7DFFFFFFFF']] only_in_pnputil=[]
* hypothesis: pnputil /resources omits every CmResourceTypeMemoryLarge descriptor, i.e. every window whose length does not fit 32 bits (>= 4 GiB)
  * windows only in cfgmgr: 3 ; min length: 8589934592 B ; all >= 4 GiB: True
  * windows only in pnputil: 0
  * verdict: **consistent with the statement**

## 4. Checks on the MERGED window set
* buses observed: 0x00, 0x01, 0x02, 0x03, 0x04, 0x65, 0x66, 0x67 ; above the legal 0xFF: none
* child window not inside any parent-bridge window: **0**
* windows outside the DSDT-declared PCI0 windows: **0**
* overlapping window pairs: 26 ; of which PARTIAL: **0**

## 5. PCI root bus (ACPI\PNP0A08)
* memory as reported by pnputil: 0xA0000-0xBFFFF, 0xC0000-0xDFFFF, 0xFA000000-0xFCFFFFFF, 0xF0000000-0xF9FFFFFF, 0xA0000000-0xDFFFFFFF
* IO as reported by pnputil: 0x0-0x3AF, 0x3E0-0xCF7, 0x3B0-0x3DF, 0xD00-0xFFFF
* NOTE: the DSDT's 64-bit window 0x460000000-0x7FFFFFFFFF is NOT in this list - it is a MemoryLarge descriptor, see section 3.

## 6. What Windows cannot answer (registered, not guessed)
* **PCI-to-PCI bridge Primary / Secondary / Subordinate Bus Number registers (config space 0x18/0x19/0x1A)** -> available=False
  * attempted: DEVPKEY_Device_DeviceNumber / DEVPKEY_Device_FunctionNumber: DO NOT EXIST on this build - the full per-device property inventory contains DEVPKEY_Device_BusNumber and DEVPKEY_Device_Address only (see prop_keys).
  * attempted: CfgMgr32 CM_Get_First_Log_Conf(ALLOC_LOG_CONF) then CM_Get_Next_Res_Des: CM_Get_First_Res_Des is NOT exported by cfgmgr32.dll on this Windows build (string-scanned every DLL in System32: 0 hits), and calling CM_Get_Next_Res_Des with a NULL current handle returns CR_INVALID_FLAG (4).
  * proxy: primary = the bridge's own DEVPKEY_Device_BusNumber (reported); secondary and subordinate are DERIVED from the buses of the functions Windows enumerated underneath the bridge.
  * consequence: a derived range cannot distinguish 'bridge claims a wider bus range than it uses' from 'bridge claims exactly what it uses'; a childless bridge yields unknown, not empty. The question 'do two bridges claim overlapping bus ranges?' CANNOT be answered from Windows data.
* **bridge Memory Base/Limit and Prefetchable Memory Base/Limit registers** -> available=proxy only
  * attempted: raw configuration space is not exposed by any Windows user-mode API.
  * proxy: the CfgMgr32 ALLOC_LOG_CONF window records (base, end, flags) which pci.sys built from those registers, incl. CM_RESOURCE_MEMORY_PREFETCHABLE (0x04).
  * consequence: this is a decoded record, not a register read: a window that the firmware never assigned cannot be reconstructed from it, and the register's alignment/granularity bits are invisible.
* **PCI Command (0x04) / Status (0x06) registers** -> available=False
  * attempted: not exposed as a device property.
  * proxy: DEVPKEY_PciDevice_* capability bits only (AcsSupport, AriSupport, AtsSupport, BarTypes, DeviceType, ExpressSpecVersion, ...), all captured.
* **individual BAR registers with index and size encoding** -> available=proxy only
  * attempted: not exposed.
  * proxy: resource ranges give base+length; DEVPKEY_PciDevice_BarTypes gives the per-BAR type flags. The BAR *index* is not given.
* **the bridge's REQUIRED (unassigned) window, i.e. what it would request on a clean re-enumeration** -> available=False
  * attempted: Windows reports what it assigned or accepted, not the requirement list; CM_Get_First_Res_Des - the requirement-side call - is unavailable here.
* **an undocumented Binary device property on 33 devices, GUID {f0e20f09-d97a-49a9-8046-bb6e22e6bb2e}[2]** -> available=False
  * attempted: dumped as bytes for every device that carries it (96 / 184 / 360 / 1504 B).
  * attempted: it DOES carry the device's interrupt pseudo-vector (offset 64 = 0xFFFFFFFE for GPP0 = -2, matching its CfgMgr32 irq record) and 0xFEE00000 (Local APIC).
  * attempted: it does NOT carry the bridge 64-bit windows: 0x7C00000000, 0x7E01FFFFFF, 0x6C00000000 and 0x7BFFFFFFFF appear nowhere in the whole dump, in text or in the byte blobs.
  * consequence: unidentified, therefore NOT used as evidence anywhere in this document.
* **macOS's own PCI resource assignment** -> available=False
  * attempted: not observable: this machine's macOS never reaches a userland in which it could be read (docs/06 section 7).

## 7. BDF provenance
* DEVPKEY_Device_DeviceNumber present: False ; DEVPKEY_Device_FunctionNumber present: False
* devices where BusNumber / Address / LocationPaths / LocationInfo disagree: 0
