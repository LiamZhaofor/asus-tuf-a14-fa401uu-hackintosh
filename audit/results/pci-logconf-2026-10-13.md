# Registry LogConf audit - the complete firmware resource descriptors (read-only)

Source: `HKLM\SYSTEM\CurrentControlSet\Enum\PCI\<dev>\<inst>\LogConf`

* `BootConfig` = REG_RESOURCE_LIST (firmware hand-over)
* `BasicConfigVector` = REG_RESOURCE_REQUIREMENTS_LIST (range + required length)
* **MemoryLarge (Type 7) length is `length / 256`.** Type 7 length field = length/256. Proof in the module docstring; control case: the RTX 4050's Type 3 BAR3 and Type 7 BAR1 both read 0x2000000 while really being 32 MiB and 8 GiB respectively.
* **BusNumber descriptors found anywhere: 0**

## Per-device

### 00:01.1  PCI Express 根端口
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GPP0)`
* BootConfig (firmware hand-over), self-consistent=True:
  * iface=5 ownBus=0 count=3
    * Memory       0xDC000000-0xDD0FFFFF len=0x1100000 flags=0x40(ALIGN32)
    * MemoryLarge  0x7C00000000-0x7E01FFFFFF len=0x202000000 [raw field 0x2020000 x256] flags=0x244(PREFETCHABLE|ALIGN32|FLAG200)
    * Port/IO      0xF000-0xFFFF len=0x1000 flags=0xa1(READABLE|CACHEABLE|ALIGN64)
* Requirements, self-consistent=True, slot=33:
    * Memory       RANGE 0xDC000000-0xDD0FFFFF span=0x1100000 REQUIRED 0x1100000 align=0x1 free_placement=False flags=0x40(ALIGN32)
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x0 align=0x100000 free_placement=True flags=0x40(ALIGN32)
    * DevicePrivate {'option': 0, 'private_data': [1, 7, 0]}
    * MemoryLarge  RANGE 0x7C00000000-0x7E01FFFFFF span=0x202000000 REQUIRED 0x202000000 [raw field 0x2020000 x256] align=0x1 free_placement=False flags=0x244(PREFETCHABLE|ALIGN32|FLAG200)
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x0 align=0x100000 free_placement=True flags=0x44(PREFETCHABLE|ALIGN32)
    * DevicePrivate {'option': 0, 'private_data': [1, 8, 0]}
    * Port/IO      RANGE 0xF000-0xFFFF span=0x1000 REQUIRED 0x1000 align=0x1 free_placement=False flags=0xa1(READABLE|CACHEABLE|ALIGN64)
    * Port/IO      RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x0 align=0x1000 free_placement=True flags=0xa1(READABLE|CACHEABLE|ALIGN64)
    * DevicePrivate {'option': 0, 'private_data': [1, 9, 0]}
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
* 1401 capture (independent): 0xDC000000-0xDD0FFFFF(memory), 0x7C00000000-0x7E01FFFFFF(memory_large)

### 00:02.1  PCI Express 根端口
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GPP5)`
* BootConfig (firmware hand-over), self-consistent=True:
  * iface=5 ownBus=0 count=1
    * Memory       0xDDF00000-0xDDFFFFFF len=0x100000 flags=0x40(ALIGN32)
* Requirements, self-consistent=True, slot=34:
    * Memory       RANGE 0xDDF00000-0xDDFFFFFF span=0x100000 REQUIRED 0x100000 align=0x1 free_placement=False flags=0x40(ALIGN32)
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x0 align=0x100000 free_placement=True flags=0x40(ALIGN32)
    * DevicePrivate {'option': 0, 'private_data': [1, 7, 0]}
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x0 align=0x100000 free_placement=True flags=0x44(PREFETCHABLE|ALIGN32)
    * DevicePrivate {'option': 0, 'private_data': [1, 8, 0]}
    * Port/IO      RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x0 align=0x1000 free_placement=True flags=0xa1(READABLE|CACHEABLE|ALIGN64)
    * DevicePrivate {'option': 0, 'private_data': [1, 9, 0]}
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
* 1401 capture (independent): 0xDDF00000-0xDDFFFFFF(memory)

### 00:02.2  PCI Express 根端口
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GPP6)`
* BootConfig (firmware hand-over), self-consistent=True:
  * iface=5 ownBus=0 count=1
    * Memory       0xDDB00000-0xDDCFFFFF len=0x200000 flags=0x40(ALIGN32)
* Requirements, self-consistent=True, slot=66:
    * Memory       RANGE 0xDDB00000-0xDDCFFFFF span=0x200000 REQUIRED 0x200000 align=0x1 free_placement=False flags=0x40(ALIGN32)
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x0 align=0x100000 free_placement=True flags=0x40(ALIGN32)
    * DevicePrivate {'option': 0, 'private_data': [1, 7, 0]}
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x0 align=0x100000 free_placement=True flags=0x44(PREFETCHABLE|ALIGN32)
    * DevicePrivate {'option': 0, 'private_data': [1, 8, 0]}
    * Port/IO      RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x0 align=0x1000 free_placement=True flags=0xa1(READABLE|CACHEABLE|ALIGN64)
    * DevicePrivate {'option': 0, 'private_data': [1, 9, 0]}
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
* 1401 capture (independent): 0xDDB00000-0xDDCFFFFF(memory), 0x7FFFF00000-0x7FFFFFFFFF(memory)

### 00:02.4  PCI Express 根端口
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GPP8)`
* BootConfig (firmware hand-over), self-consistent=True:
  * iface=5 ownBus=0 count=1
    * Memory       0xDDE00000-0xDDEFFFFF len=0x100000 flags=0x40(ALIGN32)
* Requirements, self-consistent=True, slot=130:
    * Memory       RANGE 0xDDE00000-0xDDEFFFFF span=0x100000 REQUIRED 0x100000 align=0x1 free_placement=False flags=0x40(ALIGN32)
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x0 align=0x100000 free_placement=True flags=0x40(ALIGN32)
    * DevicePrivate {'option': 0, 'private_data': [1, 7, 0]}
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x0 align=0x100000 free_placement=True flags=0x44(PREFETCHABLE|ALIGN32)
    * DevicePrivate {'option': 0, 'private_data': [1, 8, 0]}
    * Port/IO      RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x0 align=0x1000 free_placement=True flags=0xa1(READABLE|CACHEABLE|ALIGN64)
    * DevicePrivate {'option': 0, 'private_data': [1, 9, 0]}
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
* 1401 capture (independent): 0xDDE00000-0xDDEFFFFF(memory)

### 00:03.1  PCI Express 根端口
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GP11)`
* BootConfig (firmware hand-over), self-consistent=True:
  * iface=5 ownBus=0 count=3
    * Memory       0xC4000000-0xDBFFFFFF len=0x18000000 flags=0x40(ALIGN32)
    * MemoryLarge  0x6C00000000-0x7BFFFFFFFF len=0x1000000000 [raw field 0x10000000 x256] flags=0x244(PREFETCHABLE|ALIGN32|FLAG200)
    * Port/IO      0xA000-0xDFFF len=0x4000 flags=0xa1(READABLE|CACHEABLE|ALIGN64)
* Requirements, self-consistent=True, slot=35:
    * Memory       RANGE 0xC4000000-0xDBFFFFFF span=0x18000000 REQUIRED 0x18000000 align=0x1 free_placement=False flags=0x40(ALIGN32)
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x0 align=0x100000 free_placement=True flags=0x40(ALIGN32)
    * DevicePrivate {'option': 0, 'private_data': [1, 7, 0]}
    * MemoryLarge  RANGE 0x6C00000000-0x7BFFFFFFFF span=0x1000000000 REQUIRED 0x1000000000 [raw field 0x10000000 x256] align=0x1 free_placement=False flags=0x244(PREFETCHABLE|ALIGN32|FLAG200)
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x0 align=0x100000 free_placement=True flags=0x44(PREFETCHABLE|ALIGN32)
    * DevicePrivate {'option': 0, 'private_data': [1, 8, 0]}
    * Port/IO      RANGE 0xA000-0xDFFF span=0x4000 REQUIRED 0x4000 align=0x1 free_placement=False flags=0xa1(READABLE|CACHEABLE|ALIGN64)
    * Port/IO      RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x0 align=0x1000 free_placement=True flags=0xa1(READABLE|CACHEABLE|ALIGN64)
    * DevicePrivate {'option': 0, 'private_data': [1, 9, 0]}
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
* 1401 capture (independent): 0xC4000000-0xDBFFFFFF(memory), 0x6C00000000-0x7BFFFFFFFF(memory_large)

### 00:08.1  PCI Express 根端口
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GP17)`
* BootConfig (firmware hand-over), self-consistent=True:
  * iface=5 ownBus=0 count=3
    * Memory       0xDD200000-0xDD7FFFFF len=0x600000 flags=0x40(ALIGN32)
    * Memory       0x7E10000000-0x7E207FFFFF len=0x10800000 flags=0x44(PREFETCHABLE|ALIGN32)
    * Port/IO      0xE000-0xEFFF len=0x1000 flags=0xa1(READABLE|CACHEABLE|ALIGN64)
* Requirements, self-consistent=True, slot=40:
    * Memory       RANGE 0xDD200000-0xDD7FFFFF span=0x600000 REQUIRED 0x600000 align=0x1 free_placement=False flags=0x40(ALIGN32)
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x0 align=0x100000 free_placement=True flags=0x40(ALIGN32)
    * DevicePrivate {'option': 0, 'private_data': [1, 7, 0]}
    * Memory       RANGE 0x7E10000000-0x7E207FFFFF span=0x10800000 REQUIRED 0x10800000 align=0x1 free_placement=False flags=0x44(PREFETCHABLE|ALIGN32)
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x0 align=0x100000 free_placement=True flags=0x44(PREFETCHABLE|ALIGN32)
    * DevicePrivate {'option': 0, 'private_data': [1, 8, 0]}
    * Port/IO      RANGE 0xE000-0xEFFF span=0x1000 REQUIRED 0x1000 align=0x1 free_placement=False flags=0xa1(READABLE|CACHEABLE|ALIGN64)
    * Port/IO      RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x0 align=0x1000 free_placement=True flags=0xa1(READABLE|CACHEABLE|ALIGN64)
    * DevicePrivate {'option': 0, 'private_data': [1, 9, 0]}
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0x0..0xFFFFFFFF
* 1401 capture (independent): 0xDD200000-0xDD7FFFFF(memory), 0x7E10000000-0x7E207FFFFF(memory)

### 00:08.2  PCI Express 根端口
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GP18)`
* BootConfig (firmware hand-over), self-consistent=True:
  * iface=5 ownBus=0 count=2
    * Memory       0xDDD00000-0xDDDFFFFF len=0x100000 flags=0x40(ALIGN32)
    * Memory       0x7E20900000-0x7E209FFFFF len=0x100000 flags=0x44(PREFETCHABLE|ALIGN32)
* Requirements, self-consistent=True, slot=72:
    * Memory       RANGE 0xDDD00000-0xDDDFFFFF span=0x100000 REQUIRED 0x100000 align=0x1 free_placement=False flags=0x40(ALIGN32)
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x0 align=0x100000 free_placement=True flags=0x40(ALIGN32)
    * DevicePrivate {'option': 0, 'private_data': [1, 7, 0]}
    * Memory       RANGE 0x7E20900000-0x7E209FFFFF span=0x100000 REQUIRED 0x100000 align=0x1 free_placement=False flags=0x44(PREFETCHABLE|ALIGN32)
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x0 align=0x100000 free_placement=True flags=0x44(PREFETCHABLE|ALIGN32)
    * DevicePrivate {'option': 0, 'private_data': [1, 8, 0]}
    * Port/IO      RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x0 align=0x1000 free_placement=True flags=0xa1(READABLE|CACHEABLE|ALIGN64)
    * DevicePrivate {'option': 0, 'private_data': [1, 9, 0]}
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0x0..0xFFFFFFFF
* 1401 capture (independent): 0xDDD00000-0xDDDFFFFF(memory), 0x7E20900000-0x7E209FFFFF(memory)

### 00:08.3  PCI Express 根端口
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GP19)`
* BootConfig (firmware hand-over), self-consistent=True:
  * iface=5 ownBus=0 count=1
    * Memory       0xDD800000-0xDDAFFFFF len=0x300000 flags=0x40(ALIGN32)
* Requirements, self-consistent=True, slot=104:
    * Memory       RANGE 0xDD800000-0xDDAFFFFF span=0x300000 REQUIRED 0x300000 align=0x1 free_placement=False flags=0x40(ALIGN32)
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x0 align=0x100000 free_placement=True flags=0x40(ALIGN32)
    * DevicePrivate {'option': 0, 'private_data': [1, 7, 0]}
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x0 align=0x100000 free_placement=True flags=0x44(PREFETCHABLE|ALIGN32)
    * DevicePrivate {'option': 0, 'private_data': [1, 8, 0]}
    * Port/IO      RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x0 align=0x1000 free_placement=True flags=0xa1(READABLE|CACHEABLE|ALIGN64)
    * DevicePrivate {'option': 0, 'private_data': [1, 9, 0]}
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0x0..0xFFFFFFFF
* 1401 capture (independent): 0xDD800000-0xDDAFFFFF(memory)

### 01:00.0  NVIDIA GeForce RTX 4050 Laptop GPU
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GPP0)#ACPI(PEGP)`
* BootConfig (firmware hand-over), self-consistent=True:
  * iface=5 ownBus=1 count=4
    * Memory       0xDC000000-0xDCFFFFFF len=0x1000000 flags=0x80(ALIGN64)
    * MemoryLarge  0x7C00000000-0x7DFFFFFFFF len=0x200000000 [raw field 0x2000000 x256] flags=0x284(PREFETCHABLE|ALIGN64|FLAG200)
    * Memory       0x7E00000000-0x7E01FFFFFF len=0x2000000 flags=0x84(PREFETCHABLE|ALIGN64)
    * Port/IO      0xF000-0xF07F len=0x80 flags=0x131(READABLE|ALIAS|CACHEABLE)
* Requirements, self-consistent=True, slot=0:
    * Memory       RANGE 0xDC000000-0xDCFFFFFF span=0x1000000 REQUIRED 0x1000000 align=0x1 free_placement=False flags=0x80(ALIGN64)
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x1000000 align=0x1000000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate {'option': 0, 'private_data': [1, 0, 0]}
    * MemoryLarge  RANGE 0x7C00000000-0x7DFFFFFFFF span=0x200000000 REQUIRED 0x200000000 [raw field 0x2000000 x256] align=0x1 free_placement=False flags=0x284(PREFETCHABLE|ALIGN64|FLAG200)
    * MemoryLarge  RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x200000000 [raw field 0x2000000 x256] align=0x2000000 free_placement=True flags=0x284(PREFETCHABLE|ALIGN64|FLAG200)
    * DevicePrivate {'option': 0, 'private_data': [1, 1, 0]}
    * Memory       RANGE 0x7E00000000-0x7E01FFFFFF span=0x2000000 REQUIRED 0x2000000 align=0x1 free_placement=False flags=0x84(PREFETCHABLE|ALIGN64)
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x2000000 align=0x2000000 free_placement=True flags=0x84(PREFETCHABLE|ALIGN64)
    * DevicePrivate {'option': 0, 'private_data': [1, 3, 0]}
    * Port/IO      RANGE 0xF000-0xF07F span=0x80 REQUIRED 0x80 align=0x1 free_placement=False flags=0x131(READABLE|ALIAS|CACHEABLE)
    * Port/IO      RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x80 align=0x80 free_placement=True flags=0x131(READABLE|ALIAS|CACHEABLE)
    * DevicePrivate {'option': 0, 'private_data': [1, 5, 0]}
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0x0..0xFFFFFFFF
* 1401 capture (independent): 0xDC000000-0xDCFFFFFF(memory), 0x7C00000000-0x7DFFFFFFFF(memory_large), 0x7E00000000-0x7E01FFFFFF(memory)

### 01:00.1  High Definition Audio 控制器
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GPP0)#ACPI(NHDA)`
* Requirements, self-consistent=True, slot=32:
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x4000 align=0x4000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate {'option': 0, 'private_data': [1, 0, 0]}
    * Interrupt   vector 0x0..0xFFFFFFFF
* 1401 capture (independent): 0xDD0FC000-0xDD0FFFFF(memory)

### 02:00.0  Realtek PCIE CardReader
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GPP5)#ACPI(DEV0)`
* Requirements, self-consistent=True, slot=0:
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x1000 align=0x1000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate {'option': 0, 'private_data': [1, 1, 0]}
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0x0..0xFFFFFFFF
* 1401 capture (independent): 0xDDFFF000-0xDDFFFFFF(memory)

### 03:00.0  MediaTek Wi-Fi 6E MT7922 (RZ616) 160MHz Wireless LAN Card
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GPP6)#ACPI(WLAN)`
* Requirements, self-consistent=True, slot=0:
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x100000 align=0x100000 free_placement=True flags=0x84(PREFETCHABLE|ALIGN64)
    * DevicePrivate {'option': 0, 'private_data': [1, 0, 0]}
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x8000 align=0x8000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate {'option': 0, 'private_data': [1, 2, 0]}
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0x0..0xFFFFFFFF
* 1401 capture (independent): 0x7FFFF00000-0x7FFFFFFFFF(memory), 0xDDCF8000-0xDDCFFFFF(memory)

### 04:00.0  标准 NVM Express 控制器
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GPP8)#ACPI(NVME)`
* BootConfig (firmware hand-over), self-consistent=True:
  * iface=5 ownBus=4 count=1
    * Memory       0xDDE00000-0xDDE03FFF len=0x4000 flags=0x80(ALIGN64)
* Requirements, self-consistent=False, slot=0:
    * Memory       RANGE 0xDDE00000-0xDDE03FFF span=0x4000 REQUIRED 0x4000 align=0x1 free_placement=False flags=0x80(ALIGN64)
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x4000 align=0x4000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate {'option': 0, 'private_data': [1, 0, 0]}
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Memory       RANGE 0xDDE00000-0xDDE03FFF span=0x4000 REQUIRED 0x4000 align=0x1 free_placement=False flags=0x80(ALIGN64)
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x4000 align=0x4000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate {'option': 0, 'private_data': [1, 0, 0]}
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0x0..0xFFFFFFFF
* 1401 capture (independent): 0xDDE00000-0xDDE03FFF(memory)

### 65:00.0  AMD Radeon 780M Graphics
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GP17)#ACPI(VGA_)`
* BootConfig (firmware hand-over), self-consistent=True:
  * iface=5 ownBus=101 count=3
    * Memory       0x7E10000000-0x7E1FFFFFFF len=0x10000000 flags=0x84(PREFETCHABLE|ALIGN64)
    * Memory       0xDD200000-0xDD3FFFFF len=0x200000 flags=0x84(PREFETCHABLE|ALIGN64)
    * Memory       0xDD700000-0xDD77FFFF len=0x80000 flags=0x80(ALIGN64)
* Requirements, self-consistent=False, slot=0:
    * Memory       RANGE 0x7E10000000-0x7E1FFFFFFF span=0x10000000 REQUIRED 0x10000000 align=0x1 free_placement=False flags=0x84(PREFETCHABLE|ALIGN64)
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x10000000 align=0x10000000 free_placement=True flags=0x84(PREFETCHABLE|ALIGN64)
    * DevicePrivate {'option': 0, 'private_data': [1, 0, 0]}
    * Memory       RANGE 0xDD200000-0xDD3FFFFF span=0x200000 REQUIRED 0x200000 align=0x1 free_placement=False flags=0x84(PREFETCHABLE|ALIGN64)
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x200000 align=0x200000 free_placement=True flags=0x84(PREFETCHABLE|ALIGN64)
    * DevicePrivate {'option': 0, 'private_data': [1, 2, 0]}
    * Port/IO      RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x100 align=0x100 free_placement=True flags=0x131(READABLE|ALIAS|CACHEABLE)
    * DevicePrivate {'option': 0, 'private_data': [1, 4, 0]}
    * Memory       RANGE 0xDD700000-0xDD77FFFF span=0x80000 REQUIRED 0x80000 align=0x1 free_placement=False flags=0x80(ALIGN64)
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x80000 align=0x80000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate {'option': 0, 'private_data': [1, 5, 0]}
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Memory       RANGE 0x7E10000000-0x7E1FFFFFFF span=0x10000000 REQUIRED 0x10000000 align=0x1 free_placement=False flags=0x84(PREFETCHABLE|ALIGN64)
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x10000000 align=0x10000000 free_placement=True flags=0x84(PREFETCHABLE|ALIGN64)
    * DevicePrivate {'option': 0, 'private_data': [1, 0, 0]}
    * Memory       RANGE 0xDD200000-0xDD3FFFFF span=0x200000 REQUIRED 0x200000 align=0x1 free_placement=False flags=0x84(PREFETCHABLE|ALIGN64)
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x200000 align=0x200000 free_placement=True flags=0x84(PREFETCHABLE|ALIGN64)
    * DevicePrivate {'option': 0, 'private_data': [1, 2, 0]}
    * Port/IO      RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x100 align=0x100 free_placement=True flags=0x131(READABLE|ALIAS|CACHEABLE)
    * DevicePrivate {'option': 0, 'private_data': [1, 4, 0]}
    * Memory       RANGE 0xDD700000-0xDD77FFFF span=0x80000 REQUIRED 0x80000 align=0x1 free_placement=False flags=0x80(ALIGN64)
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x80000 align=0x80000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate {'option': 0, 'private_data': [1, 5, 0]}
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0x0..0xFFFFFFFF
* 1401 capture (independent): 0x7E10000000-0x7E1FFFFFFF(memory), 0xDD200000-0xDD3FFFFF(memory), 0xDD700000-0xDD77FFFF(memory)

### 65:00.1  High Definition Audio Bus
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GP17)#ACPI(HDAU)`
* Requirements, self-consistent=True, slot=32:
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x4000 align=0x4000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate {'option': 0, 'private_data': [1, 0, 0]}
    * Interrupt   vector 0x0..0xFFFFFFFF
* 1401 capture (independent): 0xDD7F8000-0xDD7FBFFF(memory)

### 65:00.2  AMD PSP 11.0 Device
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GP17)#PCI(0002)`
* Requirements, self-consistent=False, slot=64:
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x100000 align=0x100000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate {'option': 0, 'private_data': [1, 2, 0]}
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x2000 align=0x2000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate {'option': 0, 'private_data': [1, 5, 0]}
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x100000 align=0x100000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate {'option': 0, 'private_data': [1, 2, 0]}
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x2000 align=0x2000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate {'option': 0, 'private_data': [1, 5, 0]}
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0x0..0xFFFFFFFF
* 1401 capture (independent): 0xDD600000-0xDD6FFFFF(memory), 0xDD7FE000-0xDD7FFFFF(memory)

### 65:00.3  AMD USB 3.10 可扩展主机控制器 - 1.20 (Microsoft)
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GP17)#ACPI(XHC0)`
* BootConfig (firmware hand-over), self-consistent=True:
  * iface=5 ownBus=101 count=1
    * Memory       0xDD500000-0xDD5FFFFF len=0x100000 flags=0x80(ALIGN64)
* Requirements, self-consistent=True, slot=96:
    * Memory       RANGE 0xDD500000-0xDD5FFFFF span=0x100000 REQUIRED 0x100000 align=0x1 free_placement=False flags=0x80(ALIGN64)
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x100000 align=0x100000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate {'option': 0, 'private_data': [1, 0, 0]}
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0x0..0xFFFFFFFF
* 1401 capture (independent): 0xDD500000-0xDD5FFFFF(memory)

### 65:00.4  AMD USB 3.10 可扩展主机控制器 - 1.20 (Microsoft)
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GP17)#ACPI(XHC1)`
* Requirements, self-consistent=True, slot=128:
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x100000 align=0x100000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate {'option': 0, 'private_data': [1, 0, 0]}
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0x0..0xFFFFFFFF
* 1401 capture (independent): 0xDD400000-0xDD4FFFFF(memory)

### 65:00.5  AMD Audio CoProcessor
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GP17)#ACPI(ACP_)`
* Requirements, self-consistent=True, slot=160:
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x40000 align=0x40000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate {'option': 0, 'private_data': [1, 0, 0]}
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x800000 align=0x800000 free_placement=True flags=0x84(PREFETCHABLE|ALIGN64)
    * DevicePrivate {'option': 0, 'private_data': [1, 2, 0]}
    * Interrupt   vector 0x0..0xFFFFFFFF
* 1401 capture (independent): 0xDD780000-0xDD7BFFFF(memory), 0x7E20000000-0x7E207FFFFF(memory)

### 65:00.6  High Definition Audio 控制器
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GP17)#ACPI(AZAL)`
* BootConfig (firmware hand-over), self-consistent=True:
  * iface=5 ownBus=101 count=1
    * Memory       0xDD7C0000-0xDD7C7FFF len=0x8000 flags=0x80(ALIGN64)
* Requirements, self-consistent=True, slot=192:
    * Memory       RANGE 0xDD7C0000-0xDD7C7FFF span=0x8000 REQUIRED 0x8000 align=0x1 free_placement=False flags=0x80(ALIGN64)
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x8000 align=0x8000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate {'option': 0, 'private_data': [1, 0, 0]}
    * Interrupt   vector 0x0..0xFFFFFFFF
* 1401 capture (independent): 0xDD7C0000-0xDD7C7FFF(memory)

### 66:00.0  AMD PCI
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GP18)#PCI(0000)`
* Requirements, self-consistent=True, slot=0:
    * Interrupt   vector 0xFFFFFFFB..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE

### 66:00.1  NPU Compute Accelerator Device
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GP18)#ACPI(NPU_)`
* Requirements, self-consistent=False, slot=32:
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x80000 align=0x80000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate {'option': 0, 'private_data': [1, 0, 0]}
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x2000 align=0x2000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate {'option': 0, 'private_data': [1, 1, 0]}
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x40000 align=0x40000 free_placement=True flags=0x84(PREFETCHABLE|ALIGN64)
    * DevicePrivate {'option': 0, 'private_data': [1, 2, 0]}
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x40000 align=0x40000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate {'option': 0, 'private_data': [1, 4, 0]}
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x80000 align=0x80000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate {'option': 0, 'private_data': [1, 0, 0]}
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x2000 align=0x2000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate {'option': 0, 'private_data': [1, 1, 0]}
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x40000 align=0x40000 free_placement=True flags=0x84(PREFETCHABLE|ALIGN64)
    * DevicePrivate {'option': 0, 'private_data': [1, 2, 0]}
    * Memory       RANGE 0x0-0xFFFFFFFF span=0x100000000 REQUIRED 0x40000 align=0x40000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate {'option': 0, 'private_data': [1, 4, 0]}
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0x0..0xFFFFFFFF
* 1401 capture (independent): 0xDDD80000-0xDDDFFFFF(memory), 0xDDD3E000-0xDDD3FFFF(memory), 0x7E209C0000-0x7E209FFFFF(memory), 0xDDD40000-0xDDD7FFFF(memory)

### 67:00.3  AMD USB 3.10 可扩展主机控制器 - 1.20 (Microsoft)
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GP19)#ACPI(XHC3)`
* BootConfig (firmware hand-over), self-consistent=True:
  * iface=5 ownBus=103 count=1
    * Memory       0xDD900000-0xDD9FFFFF len=0x100000 flags=0x80(ALIGN64)
* Requirements, self-consistent=True, slot=96:
    * Memory       RANGE 0xDD900000-0xDD9FFFFF span=0x100000 REQUIRED 0x100000 align=0x1 free_placement=False flags=0x80(ALIGN64)
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x100000 align=0x100000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate {'option': 0, 'private_data': [1, 0, 0]}
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0x0..0xFFFFFFFF
* 1401 capture (independent): 0xDD900000-0xDD9FFFFF(memory)

### 67:00.4  AMD USB 3.10 可扩展主机控制器 - 1.20 (Microsoft)
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GP19)#ACPI(XHC4)`
* BootConfig (firmware hand-over), self-consistent=True:
  * iface=5 ownBus=103 count=1
    * Memory       0xDD800000-0xDD8FFFFF len=0x100000 flags=0x80(ALIGN64)
* Requirements, self-consistent=True, slot=128:
    * Memory       RANGE 0xDD800000-0xDD8FFFFF span=0x100000 REQUIRED 0x100000 align=0x1 free_placement=False flags=0x80(ALIGN64)
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x100000 align=0x100000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate {'option': 0, 'private_data': [1, 0, 0]}
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0x0..0xFFFFFFFF
* 1401 capture (independent): 0xDD800000-0xDD8FFFFF(memory)

### 67:00.5  USB4(TM) 主机路由器 (Microsoft)
* ACPI: `ACPI(_SB_)#ACPI(PCI0)#ACPI(GP19)#ACPI(NHI0)`
* BootConfig (firmware hand-over), self-consistent=True:
  * iface=5 ownBus=103 count=1
    * Memory       0xDDA00000-0xDDA7FFFF len=0x80000 flags=0x80(ALIGN64)
* Requirements, self-consistent=False, slot=160:
    * Memory       RANGE 0xDDA00000-0xDDA7FFFF span=0x80000 REQUIRED 0x80000 align=0x1 free_placement=False flags=0x80(ALIGN64)
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x80000 align=0x80000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate {'option': 0, 'private_data': [1, 0, 0]}
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Memory       RANGE 0xDDA00000-0xDDA7FFFF span=0x80000 REQUIRED 0x80000 align=0x1 free_placement=False flags=0x80(ALIGN64)
    * Memory       RANGE 0x0-0xFFFFFFFFFFFFFFFF span=0x10000000000000000 REQUIRED 0x80000 align=0x80000 free_placement=True flags=0x80(ALIGN64)
    * DevicePrivate {'option': 0, 'private_data': [1, 0, 0]}
    * Interrupt   vector 0xFFFFFFFE..0xFFFFFFFE
    * Interrupt   vector 0x0..0xFFFFFFFF
* 1401 capture (independent): 0xDDA00000-0xDDA7FFFF(memory)
