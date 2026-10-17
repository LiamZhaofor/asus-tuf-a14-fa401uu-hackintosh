# Round 9 stage 0 - snapshot A (2026-10-17 22:51, Windows, read-only)

> **No USB4/Thunderbolt PCIe-tunnelling device was available**, so snapshot B (device attached) could not be taken.
> Snapshot A is still useful: it is the live baseline for the next attempt, and it documents a platform-state change (see docs/10 section 6.3).
> This is the SANITISED output of `audit/pci-windows-audit.py` / `audit/pci-logconf-audit.py`; the raw PnP XML and the raw LogConf dump stay local (they carry instance IDs).

# Registry LogConf audit - firmware resource descriptors (read-only)

Source: `HKLM\SYSTEM\CurrentControlSet\Enum\PCI\<dev>\<inst>\LogConf`

* `BootConfig` = REG_RESOURCE_LIST (firmware hand-over)
* `BasicConfigVector` = REG_RESOURCE_REQUIREMENTS_LIST (range + required length)
* **Large-memory rule**: CM_RESOURCE_MEMORY_LARGE_40 (0x0200): length = raw << 8; CM_RESOURCE_MEMORY_LARGE_48 (0x0400): length = raw << 16; CM_RESOURCE_MEMORY_LARGE_64 (0x0800): length = raw << 32; none set: reported ambiguous; never guessed
* **BusNumber descriptors found: 0**
* **Fully parsed**: BootConfig 17/17, Requirements 25/25
* **Parser problems**: 6

## Parser problems (no conclusion may rest on these values)
* `66:00.0` Requirements: 1 trailing descriptor(s) beyond the declared Count
* `67:00.1` Requirements: 1 trailing descriptor(s) beyond the declared Count
* `66:00.2` Requirements: 1 trailing descriptor(s) beyond the declared Count
* `68:00.5` Requirements: 1 trailing descriptor(s) beyond the declared Count
* `02:00.0` Requirements: 1 trailing descriptor(s) beyond the declared Count
* `05:00.0` Requirements: 1 trailing descriptor(s) beyond the declared Count

## Per-device

### 00:01.1  PCI Express 根端口
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GPP0)`
* BootConfig (firmware hand-over), self-consistent=True:
  * iface=5 ownBus=0 count=3
    * Memory       0xDC000000-0xDD0FFFFF len=0x1100000 flags=0x40(ALIGN32)
    * MemoryLarge  0x7C00000000-0x7E01FFFFFF len=0x202000000 [raw 0x2020000 << 8] flags=0x244(PREFETCHABLE|ALIGN32|LARGE40)
    * Port/IO      0xF000-0xFFFF len=0x1000 flags=0xa1(READABLE|CACHEABLE|ALIGN64)
* Requirements, self-consistent=True slot=33 alts=1 trailing=0:
  * list v=1 r=1 count=10 trailing=0
    * Memory       RANGE 0xDC000000-0xDD0FFFFF span=0x1100000 REQUIRED 0x1100000 align=0x1 free_placement=False flags=0x40(ALIGN32)
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x0 align=0x100000 free_placement=None flags=0x40(ALIGN32)
    * DevicePrivate data=['0x1', '0x7', '0x0']
    * MemoryLarge  RANGE 0x7C00000000-0x7E01FFFFFF span=0x202000000 REQUIRED 0x202000000 align=0x100 [raw len 0x2020000 << 8] free_placement=False flags=0x244(PREFETCHABLE|ALIGN32|LARGE40)
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x0 align=0x100000 free_placement=None flags=0x44(PREFETCHABLE|ALIGN32)
    * DevicePrivate data=['0x1', '0x8', '0x0']
    * Port/IO      RANGE 0xF000-0xFFFF span=0x1000 REQUIRED 0x1000 align=0x1 free_placement=False flags=0xa1(READABLE|CACHEABLE|ALIGN64)
    * Port/IO      RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x0 align=0x1000 free_placement=None flags=0xa1(READABLE|CACHEABLE|ALIGN64)
    * DevicePrivate data=['0x1', '0x9', '0x0']
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE

### 00:01.2  PCI Express 根端口
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GPP1)`
* BootConfig (firmware hand-over), self-consistent=True:
  * iface=5 ownBus=0 count=1
    * Memory       0xDE000000-0xDE0FFFFF len=0x100000 flags=0x40(ALIGN32)
* Requirements, self-consistent=True slot=65 alts=1 trailing=0:
  * list v=1 r=1 count=8 trailing=0
    * Memory       RANGE 0xDE000000-0xDE0FFFFF span=0x100000 REQUIRED 0x100000 align=0x1 free_placement=False flags=0x40(ALIGN32)
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x0 align=0x100000 free_placement=None flags=0x40(ALIGN32)
    * DevicePrivate data=['0x1', '0x7', '0x0']
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x0 align=0x100000 free_placement=None flags=0x44(PREFETCHABLE|ALIGN32)
    * DevicePrivate data=['0x1', '0x8', '0x0']
    * Port/IO      RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x0 align=0x1000 free_placement=None flags=0xa1(READABLE|CACHEABLE|ALIGN64)
    * DevicePrivate data=['0x1', '0x9', '0x0']
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE

### 00:02.1  PCI Express 根端口
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GPP5)`
* BootConfig (firmware hand-over), self-consistent=True:
  * iface=5 ownBus=0 count=1
    * Memory       0xDDF00000-0xDDFFFFFF len=0x100000 flags=0x40(ALIGN32)
* Requirements, self-consistent=True slot=34 alts=1 trailing=0:
  * list v=1 r=1 count=8 trailing=0
    * Memory       RANGE 0xDDF00000-0xDDFFFFFF span=0x100000 REQUIRED 0x100000 align=0x1 free_placement=False flags=0x40(ALIGN32)
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x0 align=0x100000 free_placement=None flags=0x40(ALIGN32)
    * DevicePrivate data=['0x1', '0x7', '0x0']
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x0 align=0x100000 free_placement=None flags=0x44(PREFETCHABLE|ALIGN32)
    * DevicePrivate data=['0x1', '0x8', '0x0']
    * Port/IO      RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x0 align=0x1000 free_placement=None flags=0xa1(READABLE|CACHEABLE|ALIGN64)
    * DevicePrivate data=['0x1', '0x9', '0x0']
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE

### 00:02.2  PCI Express 根端口
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GPP6)`
* BootConfig (firmware hand-over), self-consistent=True:
  * iface=5 ownBus=0 count=1
    * Memory       0xDDB00000-0xDDCFFFFF len=0x200000 flags=0x40(ALIGN32)
* Requirements, self-consistent=True slot=66 alts=1 trailing=0:
  * list v=1 r=1 count=8 trailing=0
    * Memory       RANGE 0xDDB00000-0xDDCFFFFF span=0x200000 REQUIRED 0x200000 align=0x1 free_placement=False flags=0x40(ALIGN32)
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x0 align=0x100000 free_placement=None flags=0x40(ALIGN32)
    * DevicePrivate data=['0x1', '0x7', '0x0']
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x0 align=0x100000 free_placement=None flags=0x44(PREFETCHABLE|ALIGN32)
    * DevicePrivate data=['0x1', '0x8', '0x0']
    * Port/IO      RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x0 align=0x1000 free_placement=None flags=0xa1(READABLE|CACHEABLE|ALIGN64)
    * DevicePrivate data=['0x1', '0x9', '0x0']
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE

### 00:02.4  PCI Express 根端口
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GPP8)`
* BootConfig (firmware hand-over), self-consistent=True:
  * iface=5 ownBus=0 count=1
    * Memory       0xDDE00000-0xDDEFFFFF len=0x100000 flags=0x40(ALIGN32)
* Requirements, self-consistent=True slot=130 alts=1 trailing=0:
  * list v=1 r=1 count=8 trailing=0
    * Memory       RANGE 0xDDE00000-0xDDEFFFFF span=0x100000 REQUIRED 0x100000 align=0x1 free_placement=False flags=0x40(ALIGN32)
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x0 align=0x100000 free_placement=None flags=0x40(ALIGN32)
    * DevicePrivate data=['0x1', '0x7', '0x0']
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x0 align=0x100000 free_placement=None flags=0x44(PREFETCHABLE|ALIGN32)
    * DevicePrivate data=['0x1', '0x8', '0x0']
    * Port/IO      RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x0 align=0x1000 free_placement=None flags=0xa1(READABLE|CACHEABLE|ALIGN64)
    * DevicePrivate data=['0x1', '0x9', '0x0']
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE

### 00:03.1  PCI Express 根端口
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GP11)`
* BootConfig (firmware hand-over), self-consistent=True:
  * iface=5 ownBus=0 count=3
    * Memory       0xC4000000-0xDBFFFFFF len=0x18000000 flags=0x40(ALIGN32)
    * MemoryLarge  0x6C00000000-0x7BFFFFFFFF len=0x1000000000 [raw 0x10000000 << 8] flags=0x244(PREFETCHABLE|ALIGN32|LARGE40)
    * Port/IO      0xA000-0xDFFF len=0x4000 flags=0xa1(READABLE|CACHEABLE|ALIGN64)
* Requirements, self-consistent=True slot=35 alts=1 trailing=0:
  * list v=1 r=1 count=10 trailing=0
    * Memory       RANGE 0xC4000000-0xDBFFFFFF span=0x18000000 REQUIRED 0x18000000 align=0x1 free_placement=False flags=0x40(ALIGN32)
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x0 align=0x100000 free_placement=None flags=0x40(ALIGN32)
    * DevicePrivate data=['0x1', '0x7', '0x0']
    * MemoryLarge  RANGE 0x6C00000000-0x7BFFFFFFFF span=0x1000000000 REQUIRED 0x1000000000 align=0x100 [raw len 0x10000000 << 8] free_placement=False flags=0x244(PREFETCHABLE|ALIGN32|LARGE40)
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x0 align=0x100000 free_placement=None flags=0x44(PREFETCHABLE|ALIGN32)
    * DevicePrivate data=['0x1', '0x8', '0x0']
    * Port/IO      RANGE 0xA000-0xDFFF span=0x4000 REQUIRED 0x4000 align=0x1 free_placement=False flags=0xa1(READABLE|CACHEABLE|ALIGN64)
    * Port/IO      RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x0 align=0x1000 free_placement=None flags=0xa1(READABLE|CACHEABLE|ALIGN64)
    * DevicePrivate data=['0x1', '0x9', '0x0']
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE

### 00:08.1  PCI Express 根端口
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GP17)`
* BootConfig (firmware hand-over), self-consistent=True:
  * iface=5 ownBus=0 count=3
    * Memory       0xDD200000-0xDD7FFFFF len=0x600000 flags=0x40(ALIGN32)
    * Memory       0x7E10000000-0x7E207FFFFF len=0x10800000 flags=0x44(PREFETCHABLE|ALIGN32)
    * Port/IO      0xE000-0xEFFF len=0x1000 flags=0xa1(READABLE|CACHEABLE|ALIGN64)
* Requirements, self-consistent=True slot=40 alts=1 trailing=0:
  * list v=1 r=1 count=11 trailing=0
    * Memory       RANGE 0xDD200000-0xDD7FFFFF span=0x600000 REQUIRED 0x600000 align=0x1 free_placement=False flags=0x40(ALIGN32)
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x0 align=0x100000 free_placement=None flags=0x40(ALIGN32)
    * DevicePrivate data=['0x1', '0x7', '0x0']
    * Memory       RANGE 0x7E10000000-0x7E207FFFFF span=0x10800000 REQUIRED 0x10800000 align=0x1 free_placement=False flags=0x44(PREFETCHABLE|ALIGN32)
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x0 align=0x100000 free_placement=None flags=0x44(PREFETCHABLE|ALIGN32)
    * DevicePrivate data=['0x1', '0x8', '0x0']
    * Port/IO      RANGE 0xE000-0xEFFF span=0x1000 REQUIRED 0x1000 align=0x1 free_placement=False flags=0xa1(READABLE|CACHEABLE|ALIGN64)
    * Port/IO      RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x0 align=0x1000 free_placement=None flags=0xa1(READABLE|CACHEABLE|ALIGN64)
    * DevicePrivate data=['0x1', '0x9', '0x0']
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0x0..0xFFFFFFFF

### 00:08.2  PCI Express 根端口
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GP18)`
* BootConfig (firmware hand-over), self-consistent=True:
  * iface=5 ownBus=0 count=2
    * Memory       0xDDD00000-0xDDDFFFFF len=0x100000 flags=0x40(ALIGN32)
    * Memory       0x7E20900000-0x7E209FFFFF len=0x100000 flags=0x44(PREFETCHABLE|ALIGN32)
* Requirements, self-consistent=True slot=72 alts=1 trailing=0:
  * list v=1 r=1 count=10 trailing=0
    * Memory       RANGE 0xDDD00000-0xDDDFFFFF span=0x100000 REQUIRED 0x100000 align=0x1 free_placement=False flags=0x40(ALIGN32)
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x0 align=0x100000 free_placement=None flags=0x40(ALIGN32)
    * DevicePrivate data=['0x1', '0x7', '0x0']
    * Memory       RANGE 0x7E20900000-0x7E209FFFFF span=0x100000 REQUIRED 0x100000 align=0x1 free_placement=False flags=0x44(PREFETCHABLE|ALIGN32)
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x0 align=0x100000 free_placement=None flags=0x44(PREFETCHABLE|ALIGN32)
    * DevicePrivate data=['0x1', '0x8', '0x0']
    * Port/IO      RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x0 align=0x1000 free_placement=None flags=0xa1(READABLE|CACHEABLE|ALIGN64)
    * DevicePrivate data=['0x1', '0x9', '0x0']
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0x0..0xFFFFFFFF

### 00:08.3  PCI Express 根端口
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GP19)`
* BootConfig (firmware hand-over), self-consistent=True:
  * iface=5 ownBus=0 count=1
    * Memory       0xDD800000-0xDDAFFFFF len=0x300000 flags=0x40(ALIGN32)
* Requirements, self-consistent=True slot=104 alts=1 trailing=0:
  * list v=1 r=1 count=9 trailing=0
    * Memory       RANGE 0xDD800000-0xDDAFFFFF span=0x300000 REQUIRED 0x300000 align=0x1 free_placement=False flags=0x40(ALIGN32)
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x0 align=0x100000 free_placement=None flags=0x40(ALIGN32)
    * DevicePrivate data=['0x1', '0x7', '0x0']
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x0 align=0x100000 free_placement=None flags=0x44(PREFETCHABLE|ALIGN32)
    * DevicePrivate data=['0x1', '0x8', '0x0']
    * Port/IO      RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x0 align=0x1000 free_placement=None flags=0xa1(READABLE|CACHEABLE|ALIGN64)
    * DevicePrivate data=['0x1', '0x9', '0x0']
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0x0..0xFFFFFFFF

### 02:00.0  标准 NVM Express 控制器
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GPP1)#ACPI(NVME)`
* BootConfig (firmware hand-over), self-consistent=True:
  * iface=5 ownBus=2 count=2
    * Memory       0xDE000000-0xDE003FFF len=0x4000 flags=0x80(ALIGN64)
    * Memory       0xDE004000-0xDE0040FF len=0x100 flags=0x80(ALIGN64)
* Requirements, self-consistent=True slot=0 alts=2 trailing=1:
  * list v=1 r=1 count=23 trailing=0
    * Memory       RANGE 0xDE000000-0xDE003FFF span=0x4000 REQUIRED 0x4000 align=0x1 free_placement=False flags=0x80(ALIGN64)
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x4000 align=0x4000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate data=['0x1', '0x0', '0x0']
    * Memory       RANGE 0xDE004000-0xDE0040FF span=0x100 REQUIRED 0x100 align=0x1 free_placement=False flags=0x80(ALIGN64)
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x100 align=0x100 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate data=['0x1', '0x4', '0x0']
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
  * list v=1 r=1 count=8 trailing=1
    * Memory       RANGE 0xDE000000-0xDE003FFF span=0x4000 REQUIRED 0x4000 align=0x1 free_placement=False flags=0x80(ALIGN64)
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x4000 align=0x4000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate data=['0x1', '0x0', '0x0']
    * Memory       RANGE 0xDE004000-0xDE0040FF span=0x100 REQUIRED 0x100 align=0x1 free_placement=False flags=0x80(ALIGN64)
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x100 align=0x100 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate data=['0x1', '0x4', '0x0']
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0x0..0xFFFFFFFF
    * Null         {'option': 0, 'share': 0, 'trailing': True}

### 03:00.0  Realtek PCIE CardReader
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GPP5)#ACPI(DEV0)`
* Requirements, self-consistent=True slot=0 alts=1 trailing=0:
  * list v=1 r=1 count=4 trailing=0
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x1000 align=0x1000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate data=['0x1', '0x1', '0x0']
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0x0..0xFFFFFFFF

### 04:00.0  MediaTek Wi-Fi 6E MT7922 (RZ616) 160MHz Wireless LAN Card
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GPP6)#ACPI(WLAN)`
* Requirements, self-consistent=True slot=0 alts=1 trailing=0:
  * list v=1 r=1 count=6 trailing=0
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x100000 align=0x100000 free_placement=True flags=0x84(PREFETCHABLE|ALIGN64)
    * DevicePrivate data=['0x1', '0x0', '0x0']
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x8000 align=0x8000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate data=['0x1', '0x2', '0x0']
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0x0..0xFFFFFFFF

### 05:00.0  标准 NVM Express 控制器
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GPP8)#ACPI(NVME)`
* BootConfig (firmware hand-over), self-consistent=True:
  * iface=5 ownBus=5 count=1
    * Memory       0xDDE00000-0xDDE03FFF len=0x4000 flags=0x80(ALIGN64)
* Requirements, self-consistent=True slot=0 alts=2 trailing=1:
  * list v=1 r=1 count=68 trailing=0
    * Memory       RANGE 0xDDE00000-0xDDE03FFF span=0x4000 REQUIRED 0x4000 align=0x1 free_placement=False flags=0x80(ALIGN64)
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x4000 align=0x4000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate data=['0x1', '0x0', '0x0']
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
  * list v=1 r=1 count=5 trailing=1
    * Memory       RANGE 0xDDE00000-0xDDE03FFF span=0x4000 REQUIRED 0x4000 align=0x1 free_placement=False flags=0x80(ALIGN64)
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x4000 align=0x4000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate data=['0x1', '0x0', '0x0']
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0x0..0xFFFFFFFF
    * Null         {'option': 0, 'share': 0, 'trailing': True}

### 66:00.0  AMD Radeon 780M Graphics
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GP17)#ACPI(VGA_)`
* BootConfig (firmware hand-over), self-consistent=True:
  * iface=5 ownBus=102 count=3
    * Memory       0x7E10000000-0x7E1FFFFFFF len=0x10000000 flags=0x84(PREFETCHABLE|ALIGN64)
    * Memory       0xDD200000-0xDD3FFFFF len=0x200000 flags=0x84(PREFETCHABLE|ALIGN64)
    * Memory       0xDD700000-0xDD77FFFF len=0x80000 flags=0x80(ALIGN64)
* Requirements, self-consistent=True slot=0 alts=2 trailing=1:
  * list v=1 r=1 count=15 trailing=0
    * Memory       RANGE 0x7E10000000-0x7E1FFFFFFF span=0x10000000 REQUIRED 0x10000000 align=0x1 free_placement=False flags=0x84(PREFETCHABLE|ALIGN64)
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x10000000 align=0x10000000 free_placement=True flags=0x84(PREFETCHABLE|ALIGN64)
    * DevicePrivate data=['0x1', '0x0', '0x0']
    * Memory       RANGE 0xDD200000-0xDD3FFFFF span=0x200000 REQUIRED 0x200000 align=0x1 free_placement=False flags=0x84(PREFETCHABLE|ALIGN64)
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x200000 align=0x200000 free_placement=True flags=0x84(PREFETCHABLE|ALIGN64)
    * DevicePrivate data=['0x1', '0x2', '0x0']
    * Port/IO      RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x100 align=0x100 free_placement=True flags=0x131(READABLE|ALIAS|CACHEABLE)
    * DevicePrivate data=['0x1', '0x4', '0x0']
    * Memory       RANGE 0xDD700000-0xDD77FFFF span=0x80000 REQUIRED 0x80000 align=0x1 free_placement=False flags=0x80(ALIGN64)
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x80000 align=0x80000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate data=['0x1', '0x5', '0x0']
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
  * list v=1 r=1 count=13 trailing=1
    * Memory       RANGE 0x7E10000000-0x7E1FFFFFFF span=0x10000000 REQUIRED 0x10000000 align=0x1 free_placement=False flags=0x84(PREFETCHABLE|ALIGN64)
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x10000000 align=0x10000000 free_placement=True flags=0x84(PREFETCHABLE|ALIGN64)
    * DevicePrivate data=['0x1', '0x0', '0x0']
    * Memory       RANGE 0xDD200000-0xDD3FFFFF span=0x200000 REQUIRED 0x200000 align=0x1 free_placement=False flags=0x84(PREFETCHABLE|ALIGN64)
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x200000 align=0x200000 free_placement=True flags=0x84(PREFETCHABLE|ALIGN64)
    * DevicePrivate data=['0x1', '0x2', '0x0']
    * Port/IO      RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x100 align=0x100 free_placement=True flags=0x131(READABLE|ALIAS|CACHEABLE)
    * DevicePrivate data=['0x1', '0x4', '0x0']
    * Memory       RANGE 0xDD700000-0xDD77FFFF span=0x80000 REQUIRED 0x80000 align=0x1 free_placement=False flags=0x80(ALIGN64)
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x80000 align=0x80000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate data=['0x1', '0x5', '0x0']
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0x0..0xFFFFFFFF
    * Null         {'option': 0, 'share': 0, 'trailing': True}

### 66:00.1  High Definition Audio Bus
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GP17)#ACPI(HDAU)`
* Requirements, self-consistent=True slot=32 alts=1 trailing=0:
  * list v=1 r=1 count=3 trailing=0
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x4000 align=0x4000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate data=['0x1', '0x0', '0x0']
    * Interrupt    vector 0x0..0xFFFFFFFF

### 66:00.2  AMD PSP 11.0 Device
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GP17)#PCI(0002)`
* Requirements, self-consistent=True slot=64 alts=2 trailing=1:
  * list v=1 r=1 count=6 trailing=0
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x100000 align=0x100000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate data=['0x1', '0x2', '0x0']
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x2000 align=0x2000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate data=['0x1', '0x5', '0x0']
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
  * list v=1 r=1 count=6 trailing=1
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x100000 align=0x100000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate data=['0x1', '0x2', '0x0']
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x2000 align=0x2000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate data=['0x1', '0x5', '0x0']
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0x0..0xFFFFFFFF
    * Null         {'option': 0, 'share': 0, 'trailing': True}

### 66:00.3  AMD USB 3.10 可扩展主机控制器 - 1.20 (Microsoft)
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GP17)#ACPI(XHC0)`
* BootConfig (firmware hand-over), self-consistent=True:
  * iface=5 ownBus=102 count=1
    * Memory       0xDD500000-0xDD5FFFFF len=0x100000 flags=0x80(ALIGN64)
* Requirements, self-consistent=True slot=96 alts=1 trailing=0:
  * list v=1 r=1 count=5 trailing=0
    * Memory       RANGE 0xDD500000-0xDD5FFFFF span=0x100000 REQUIRED 0x100000 align=0x1 free_placement=False flags=0x80(ALIGN64)
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x100000 align=0x100000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate data=['0x1', '0x0', '0x0']
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0x0..0xFFFFFFFF

### 66:00.4  AMD USB 3.10 可扩展主机控制器 - 1.20 (Microsoft)
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GP17)#ACPI(XHC1)`
* Requirements, self-consistent=True slot=128 alts=1 trailing=0:
  * list v=1 r=1 count=4 trailing=0
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x100000 align=0x100000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate data=['0x1', '0x0', '0x0']
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0x0..0xFFFFFFFF

### 66:00.5  AMD Audio CoProcessor
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GP17)#ACPI(ACP_)`
* Requirements, self-consistent=True slot=160 alts=1 trailing=0:
  * list v=1 r=1 count=5 trailing=0
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x40000 align=0x40000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate data=['0x1', '0x0', '0x0']
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x800000 align=0x800000 free_placement=True flags=0x84(PREFETCHABLE|ALIGN64)
    * DevicePrivate data=['0x1', '0x2', '0x0']
    * Interrupt    vector 0x0..0xFFFFFFFF

### 66:00.6  High Definition Audio 控制器
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GP17)#ACPI(AZAL)`
* BootConfig (firmware hand-over), self-consistent=True:
  * iface=5 ownBus=102 count=1
    * Memory       0xDD7C0000-0xDD7C7FFF len=0x8000 flags=0x80(ALIGN64)
* Requirements, self-consistent=True slot=192 alts=1 trailing=0:
  * list v=1 r=1 count=4 trailing=0
    * Memory       RANGE 0xDD7C0000-0xDD7C7FFF span=0x8000 REQUIRED 0x8000 align=0x1 free_placement=False flags=0x80(ALIGN64)
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x8000 align=0x8000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate data=['0x1', '0x0', '0x0']
    * Interrupt    vector 0x0..0xFFFFFFFF

### 67:00.0  AMD PCI
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GP18)#PCI(0000)`
* Requirements, self-consistent=True slot=0 alts=1 trailing=0:
  * list v=1 r=1 count=2 trailing=0
    * Interrupt    vector 0xFFFFFFFB..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE

### 67:00.1  NPU Compute Accelerator Device
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GP18)#ACPI(NPU_)`
* Requirements, self-consistent=True slot=32 alts=2 trailing=1:
  * list v=1 r=1 count=24 trailing=0
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x80000 align=0x80000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate data=['0x1', '0x0', '0x0']
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x2000 align=0x2000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate data=['0x1', '0x1', '0x0']
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x40000 align=0x40000 free_placement=True flags=0x84(PREFETCHABLE|ALIGN64)
    * DevicePrivate data=['0x1', '0x2', '0x0']
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x40000 align=0x40000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate data=['0x1', '0x4', '0x0']
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
  * list v=1 r=1 count=10 trailing=1
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x80000 align=0x80000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate data=['0x1', '0x0', '0x0']
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x2000 align=0x2000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate data=['0x1', '0x1', '0x0']
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x40000 align=0x40000 free_placement=True flags=0x84(PREFETCHABLE|ALIGN64)
    * DevicePrivate data=['0x1', '0x2', '0x0']
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x40000 align=0x40000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate data=['0x1', '0x4', '0x0']
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0x0..0xFFFFFFFF
    * Null         {'option': 0, 'share': 0, 'trailing': True}

### 68:00.3  AMD USB 3.10 可扩展主机控制器 - 1.20 (Microsoft)
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GP19)#ACPI(XHC3)`
* BootConfig (firmware hand-over), self-consistent=True:
  * iface=5 ownBus=104 count=1
    * Memory       0xDD900000-0xDD9FFFFF len=0x100000 flags=0x80(ALIGN64)
* Requirements, self-consistent=True slot=96 alts=1 trailing=0:
  * list v=1 r=1 count=5 trailing=0
    * Memory       RANGE 0xDD900000-0xDD9FFFFF span=0x100000 REQUIRED 0x100000 align=0x1 free_placement=False flags=0x80(ALIGN64)
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x100000 align=0x100000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate data=['0x1', '0x0', '0x0']
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0x0..0xFFFFFFFF

### 68:00.4  AMD USB 3.10 可扩展主机控制器 - 1.20 (Microsoft)
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GP19)#ACPI(XHC4)`
* BootConfig (firmware hand-over), self-consistent=True:
  * iface=5 ownBus=104 count=1
    * Memory       0xDD800000-0xDD8FFFFF len=0x100000 flags=0x80(ALIGN64)
* Requirements, self-consistent=True slot=128 alts=1 trailing=0:
  * list v=1 r=1 count=5 trailing=0
    * Memory       RANGE 0xDD800000-0xDD8FFFFF span=0x100000 REQUIRED 0x100000 align=0x1 free_placement=False flags=0x80(ALIGN64)
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x100000 align=0x100000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate data=['0x1', '0x0', '0x0']
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0x0..0xFFFFFFFF

### 68:00.5  USB4(TM) 主机路由器 (Microsoft)
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GP19)#ACPI(NHI0)`
* BootConfig (firmware hand-over), self-consistent=True:
  * iface=5 ownBus=104 count=1
    * Memory       0xDDA00000-0xDDA7FFFF len=0x80000 flags=0x80(ALIGN64)
* Requirements, self-consistent=True slot=160 alts=2 trailing=1:
  * list v=1 r=1 count=19 trailing=0
    * Memory       RANGE 0xDDA00000-0xDDA7FFFF span=0x80000 REQUIRED 0x80000 align=0x1 free_placement=False flags=0x80(ALIGN64)
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x80000 align=0x80000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate data=['0x1', '0x0', '0x0']
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
  * list v=1 r=1 count=5 trailing=1
    * Memory       RANGE 0xDDA00000-0xDDA7FFFF span=0x80000 REQUIRED 0x80000 align=0x1 free_placement=False flags=0x80(ALIGN64)
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x80000 align=0x80000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate data=['0x1', '0x0', '0x0']
    * Interrupt    vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt    vector 0x0..0xFFFFFFFF
    * Null         {'option': 0, 'share': 0, 'trailing': True}
