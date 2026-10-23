# HANDOFF — iOS 16 на Xiaomi Mi 10 Ultra (cas) — 2026-10-24

> Этот файл восстановлен по сессии `C:\ports\deepseeksessions\1session\` (4571 события, 60 ходов,
> 22.10 18:25 → 23.10 21:32 MSK). Сессия умерла не по технической причине, а по `ACCOUNT_QUOTA`
> (402 Insufficient Balance); последние ~5 ходов — пустой вывод.
> Проект: **iOS 16.7.16 (20H392) на реальном Mi 10 Ultra**, ветка-форк `proshivka/ios-cas` от
> `ios-sweet` (iOS для Redmi Note 10 Pro / sweet). Плюс отдельный, уже замороженный трек WoA.

---

## 0. TL;DR (одна минута)

* **Работает:** iOS-загрузчик (sweet shim) **грузится на SM8250**, читает UFS GPT, парсит ADT,
  копирует payload, строит boot_args и **прыгает в «ядро»** — проверено стабом, который красит
  панель синим (ARGB FF0000FF). Вся цепочка fastboot → shim → payload → jump жива.
* **Собрано:** XNU-ядро sweet собралось на GitHub Actions **успешно** — run `39995850227`
  (job `120559057075`, шаг `Build — completed/success`), артефакт **`xnu-kernel` 57.2 MB**
  (`artifacts/12519688991`) ещё не истёк. В прошлой сессии этого статуса никто не увидел.
* **Блокер:** ядро ещё **не упаковано и не загружено**. Плюс найдено и **не исправлено**:
  патчи `0016` / `0018` матчат платформу по `'IONameMatch' = 'xiaomi,sweet'`, а ADT теперь
  `xiaomi,cas` → platform expert не привяжется, ядро умрёт на старте io-дерева.
* **Пустой iOS-root:** `C:\ports\iosroot\ios16-root.img` (17 179 869 184 байт) создан
  `mkfs.hfsplus`, но **не наполнен** — WSL не имеет `hfsplus` ни модулем, ни в `/proc/filesystems`,
  `mkiosroot.sh` упал на `mount: unknown filesystem type 'hfsplus'`. Для первого запуска ядра
  root не нужен — нужен ramdisk (`tools/mkinit.py`).
* **Следующее действие (по порядку):** ① скачать артефакт `xnu-kernel` → ② починить platform-match
  под `xiaomi,cas` (и пересобрать) → ③ `tools/mkpayload.py <kernel> shim/out/cas.adt ...` →
  ④ `shim/build.sh` → ⑤ `fastboot boot` → читать fbcon-консоль.
  Если гонять ядро без пересборки — ② всё равно первым, иначе панель почернеет на IOPlatformExpert.

---

## 1. Где что лежит

| Путь | Что это |
|---|---|
| `C:\ports\ios-cas\` | **главный репозиторий** (форк `proshivka/ios-cas` от `ios-sweet`/sweet). Remote: `https://github.com/proshivka/ios-cas.git` |
| `C:\ports\ios-cas\NOTES.md` | **живой журнал работ** (488 строк, 189 КБ) — читать первым, там история milestone'ов |
| `C:\ports\ios-cas\shim\` | загрузчик sweet (start.S, mmu.c, ufs.c, fdt.c, console.c, loader.c), `build.sh` |
| `C:\ports\ios-cas\shim\out\cas.adt` | готовый ADT под cas (1080×2340, `xiaomi,cas|qcom,sm8250`, identity D22AP/iPhone10,3) |
| `C:\ports\ios-cas\shim\dtb\boot_unpacked\dtb` | live-FDT, снятый с телефона (973 989 байт) |
| `C:\ports\ios-cas\tools\mkadt.py` | генератор ADT, есть `--cas` |
| `C:\ports\ios-cas\tools\mkpayload.py` | Mach-O kernel → payload (32-байтные сегменты), `--phys/--virt/--mem/--cmdline` |
| `C:\ports\ios-cas\tools\mkstub_payload.py`, `tools/cas_stub.S` | стаб-ядро для проверки цепочки |
| `C:\ports\ios-cas\tools\mkiosroot.sh` | сборка iOS root из DMG (требует hfsplus) |
| `C:\ports\ios-cas\tools\mkinit.py` | ramdisk (то, что нужно вместо root на первом запуске) |
| `C:\ports\ios-cas\tools\qemu-sweet.py` | QEMU-двойник sweet для офлайн-проверок |
| `C:\ports\ios-cas\tools\xnu-cc.py` | офлайн compile+symbols проверка патчей |
| `C:\ports\ios-cas\xnu\patches\` | **82 патча** (0001…0081 + stage-скрипты), 0058 — HID (1 МБ), 0060/0062 — тач, 0046 — IOSurface/IOMFB |
| `C:\ports\ios-cas\.github\workflows\xnu.yml` | CI-сборка ядра (blacktop/darwin-xnu-build, macOS 13.5, SWEET) |
| `C:\ports\ipsw\iPhone10,3_16.7.16_20H392.ipsw` | 6 171 035 648 байт, sha256 `ece1194f…68fb` |
| `C:\ports\ipsw\x\` | распаковано 7z: `087-86698-044.dmg` (OS 4.41 ГБ), `087-86593-047.dmg` (SystemOS 2.55 ГБ), `087-86715-047.dmg` (AppOS), `087-86719/86622-047.dmg` (restore ramdisk) |
| `C:\ports\iosroot\ios16-root.img` | 16 ГиБ, **пустой** HFS+ (см. §5) |
| `C:\ports\live\` | рабочие скрипты и логи: `build_iosroot.sh`, `mkxnu_cas.sh`, `build_shim_cas.sh`, `build_stub.sh`, `uefi_*.log`, `.ghtoken` (PAT для CI) |
| `/opt/apfs-fuse/build/apfs-fuse` (WSL) | **собран**, симлинк в `/usr/local/bin/apfs-fuse` |
| `C:\ports\hackios\` | старый (брошенный) трек: `mkxnuimg.py`, `payload-cas.bin`, `xnu` |
| `C:\ports\Mu-Silicium\` | UEFI-трек (заброшен, но рабочие образы лежат): `build_uefi.py -d cas` |
| `C:\ports\Mu-cas*.img` | UEFI-образы: `Mu-cas.img` (рабочий, грузит Windows), `-touch`, `-acpi`, `-pwr`, `-pwr2`, `-nopwr-backup` |
| `C:\ports\WoA-Xiaomi-Mi-10-Ultra\` | драйверный репо WoA, `4cfadf0` |
| `C:\ports\handoff_*.md`, `handoff.md` | handoff'ы по WoA-треку (железо, тач, BSOD'ы) |

---

## 2. Что уже сделано в iOS-порте (статус по факту)

### 2.1 Milestones, подтверждённые на устройстве
1. **`966f7dc` — shim грузится на cas.** Fastboot → shim → экран загрузчика, UFS GPT читается,
   FDT/ADT парсятся. Вывод на панели:
   `SHIM sweet milestone 4: xnu loader`, `UFS ver=00000300 cap=1587031F`,
   `UFS probe done, reset in ~3 min`.
2. **`43a8639` → `9dbf003` — PANIC SYNC вылечен.** `struct payload_seg` = **32 байта**
   (vmaddr, vmsize, file_off, file_size), массив сегментов заканчивается на `0x2a8 + 0x20 = 0x2c8`.
   Стаб был положен на `0x2b8`, то есть **на поверх `file_off`/`file_size`** → shim читал
   `file_off = 0x14000000` (это байты инструкции `b .`!) и `file_size = 9` → data abort.
   С офсетом `0x2c8` всё пошло.
3. **`e3c8a00` — цепочка работает end-to-end.** На панели дословно:
   ```
   INITRD lo=AFFFC000 hi=AFFFC000+A38
   PHYS base=B0000000 size=09800000
   COPY dst=B0000000 src=AFFFC2C8 / sz=00000004 va=B0000000
   SEGS n=1 end=B0001000
   BOOTARG pa=B0004000 top=B000B000
   JUMP 00000000B0000000
   XNU jumping (fbcon clears screen)
   ```
   → стаб (4 инструкции заливки 1080×2340 по `0x9C000000`) красит экран **сплошным синим**,
   без паники. Пользователь подтвердил: «Только синий экран!!! Всё чисто!».

### 2.2 Ограничения, которые надо соблюдать
* `shim/mmu.c` мапит **только первые 8 ГиБ** как Device, дальше — не замаплено.
  Значит `phys_base` < `0x200000000`. Рабочее значение: `0xB0000000`
  (выше XPU-вырезов Qualcomm: ramdump_fb `0xaf000000`+16M, cdsp_sec, qseecom),
  рамадиск лежит на `0xAFFFC000` — **не перекрывать**.
* На Qualcomm каждый XPU-карв должен быть **ниже** ядра. Для bring-up `memSize ≈ 0x4d000000`
  (кончается до rmtfs `0xfde01000`).
* `start.s` мапит `[mach header .. physBase+memSize)` кэшируемыми блоками.
* Framebuffer панели (ABL/GOP): `base=0x9C000000 size=0x9A3F80`, 1080×2340.

### 2.3 CI
* Токен: `C:\ports\live\.ghtoken` (PAT, 40 симв.).
* Dispatch: `POST https://api.github.com/repos/proshivka/ios-cas/actions/workflows/xnu.yml/dispatches`
  с `{"ref":"main","inputs":{"macos_version":"13.5","kernel_config":"DEVELOPMENT","machine_config":"SWEET","keep_going":"true"}}`.
* Run `39993516436` — **cancelled** в очереди через 15 мин (не наша ошибка, просто очередь).
* Run **`39995850227` — completed / SUCCESS**, job `120559057075`, все шаги зелёные
  (Deps, Build, Package build tree, Inspect closed KDK support libs, Collect).
  Артефакты: `xnu-kernel` 57.2 MB (id `12519688991`), `xnu-buildtree` 22 MB (id `12520726265`).
* Скачивание: `GET /repos/proshivka/ios-cas/actions/artifacts/<id>/zip` c `Authorization: Bearer <token>`
  (редирект на storage, нужен `-L`).

### 2.4 Брошенные треки (не возвращаться без причины)
* **UEFI / Mu-Silicium** — `build_uefi.py -d cas` собирался (`PROGRESS - Success`), но:
  FVMAIN занят на 99% (6 268 160 из 6 270 976), новые образы (`-touch`, `-acpi`, `-pwr`)
  **убивают загрузку** («телефон просто выключился, ничего нету», «с новым boot.img кружок не
  появился»). Рабочий остался только `Mu-cas.img`. Причина не найдена, трек закрыт.
* **HackiOS** (`C:\ports\hackios`) — `xnu-cas.img`, `payload-cas.bin`, `mkxnuimg.py`.
  Отдавал `0xc000000f` / «Windows failed to start» / ребут после 10–15 с. Закрыт в пользу shim.

---

## 3. Следующие шаги (конкретно, в порядке выполнения)

1. **Скачать ядро** (артефакт ещё жив, но истечёт — качать первым делом):
   ```
   curl.exe -L -H "Authorization: Bearer $(Get-Content C:\ports\live\.ghtoken -Raw)" \
     -o C:\ports\iosroot\xnu-kernel.zip \
     https://api.github.com/repos/proshivka/ios-cas/actions/artifacts/12519688991/zip
   ```
   Внутри `out/` — kernel (`mach_kernel`/`kernel.release`/`kernel.development`).
2. **Platform-match под cas.** Найдено в конце сессии и **не применено**:
   * `0016-sweet-device-tree-platform-expert.patch:12` → `'IONameMatch' = 'xiaomi,sweet';`
   * `0018-sweet-boot-cpu-driver.patch:181` → `'IONameMatch' = 'xiaomi,sweet';`
   * `0018:187` → `'qcom,kryo470'` (это soft-match, на cas нужен `qcom,kryo585`/kona — проверить).
   Варианты: (а) в `mkadt.py --cas` дописать совместимость `xiaomi,sweet` в узел arm-io/soc,
   (б) сделать матч по любому `xiaomi,*` одной строкой (лучше — патч в xnu, тогда CI-пересборка).
   **Проверить до загрузки:** `Select-String -Path xnu\patches\*.patch -Pattern 'xiaomi,sweet'`.
3. **Упаковать:** `python tools/mkpayload.py <kernel> shim/out/cas.adt shim/out/payload-cas.bin --phys 0xB0000000 --mem 0x4d000000 --cmdline "..."`.
   Не забыть: сегменты по 32 байта, payload ниже 8 ГиБ, не перекрыть рамадиск на `0xAFFFC000`.
4. **Собрать образ shim:** `bash shim/build.sh` (Windows: через `wsl -e bash /mnt/c/ports/live/build_shim_cas.sh`).
5. **Загрузить:** `fastboot boot <образ>` (телефон в fastboot; восстановление — TWRP, Power+Vol Down).
6. **Читать консоль.** fbcon (патч 0003) рисует kprintf на панели. Полезные boot-args
   из истории sweet: `sweetsample=...`, `sweetnull=backboardd,SpringBoard`, `ignition_level=`.
7. **Позже:** ramdisk (`tools/mkinit.py`) → первая загрузка BSD-части → потом root.
   Root-образ пересобрать с `hfsplus`-юзспейсом (§5).

**Офлайн-проверка перед каждой загрузкой телефона:** `tools/xnu-cc.py` (компиляция+символы),
`tools/qemu-sweet.py` (сверить с QEMU-двойником sweet), `tools/validate-repo.py`.

---

## 4. Ключевые факты (не переоткрывать)

### Ядро / SWEET machine config
* SWEET собирается **plain arm64** (не arm64e): `HAS_APPLE_PAC` определён только для `__arm64e__`.
  Kryo 585 (cas) = ARMv8.2 → PAC нет.
* База — VMAPPLE (16K страниц, GICv3 в `pe_fiq.c`) **минус** APPLEVIRTUALPLATFORM-гиперколлы,
  **плюс** generic ARM (без Apple sysreg'ов). KDK-либы `lib<cfg>.os.*.a` не линковать.
* Таймер: XNU ждёт его на **FIQ** (`sleh_fiq` → `rtclock_intr`). SWEET: GIC **Group 1** —
  `sleh_irq` должен ack'ать `ICC_IAR1`, INTID 19 → тот же путь, SGI → `cpu_signal_handler`,
  EOI через `ICC_EOIR1`.
* SMP: open-source AppleARMSMP (`USE_APPLEARMSMP`) требует IOInterruptController (роль AIC) и
  IOPMGR (питание CPU → PSCI CPU_ON через SMC). План: встроенные IOKit-классы (`SweetGIC`,
  `SweetPMGR`, platform expert) прямо в ядро, матч через `iokit/KernelConfigTables.cpp`.
* ADT `/arm-io` ranges **не должны** вести на parent 0 (`pe_arm_get_soc_base_phys()==0`
  отключает serial) — использовать parent `0x1000000`.
* Debug-канал: патч 0003 `sweet-fbcon` — kprintf на фреймбуфер через ADT-узел `sweet-fbcon`.
* `kprintf` — **no-op до `STARTUP_SUB_KPRINTF`** (поэтому первые миллисекунды не видны;
  для этого был патч 0010 — ранние цветные полосы при MMU off).

### История зрелости sweet (что уже умеет порт)
Порт sweet прошёл путь до запуска SpringBoard: HID, IOSurface/IOMFB (0046), тач (0060/0062),
USB-ECM (0075), HFS+ (0026), AMFI/entitlements (0025/0035), AKS (0038), SMP/PSCI (0065),
8 ядер (0078), IOWatchdog (0040/0045), persistent console log (0047).
Открытые исторические баги (на sweet, скорее всего верны и на cas):
* **Дисплей** — backboardd падает в `StartWindowServer`, пока нет сервиса
  **IOMobileFramebuffer** и IOSurface; SpringBoard умирает в `FBSDisplayMonitor`.
* data migration каждый бут заново (лечится `com.apple.DataMigration.plist` `LastSystemVersion`).
* Settings SIGTRAP — force-unwrap `URL.volumeTotalCapacity` = nil на HFS+ root.
* USB-интернет: configd не поднимает `ue0` (нужны IOKit-заглушки / имя en*).

### Железо Mi 10 Ultra (cas / J1S, M2007J1SC)
* SoC **SM8250 / Kona** (Snapdragon 865), 12 ГБ LPDDR5, 256 ГБ UFS 3.1;
  панель CSOT OLED 1080×2340; фреймбуфер `0x9C000000` (size `0x9A3F80`).
* Разделы UFS: `persist`, `logdump`, `recovery`, `super`, `userdata` (f2fs),
  `esp` 0x832 МиБ, `win` 0x2C208 МиБ.
* Тач: **ST FingerTipS FTS521/FTM5**, I2C-13 (`QUPv3 SE5 @0x00A94000`, 400 кГц, 7-bit `0x49`,
  без dummy-байта), IRQ TLMM **GPIO 39** (ActiveLow/Edge), Reset **GPIO 38**,
  ACPI `ACPI\STFT0521`, AVDD через `regulator-fixed` `vreg_touch_vddio` (GPIO 69).
  На Windows: ChipId `0xC00000B5` (IO_TIMEOUT), «Пад12/13 = 0» → питание не доезжает.

### Трек Windows on ARM (для контекста, заморожен)
* Windows 11 ARM64 грузится. Драйвер `casfts.sys` в DriverStore,
  `HKLM\SYSTEM\CurrentControlSet001\Enum\ACPI\STFT0521\1 LowerFilters=casfts`.
  Code 39/0xBE/0x37 вылечен, драйвер грузится, HID-стек и SPB ок.
* BSOD `CLOCK_WATCHDOG_TIMEOUT (0x101)` — на итерации с драйвером.
  BSOD `WHEA_UNCORRECTABLE_ERROR (0x124)` — на записи в TLMM GPIO69
  (на ARM64 это обычно synchronous external abort / SError).
* Вывод друга (`proshivka`): PEP не нужен, нужен **PMIC** — питание тача из Windows не поднять.
  Из Windows писать в TLMM нельзя (второй маппинг той же физики) — только Resource Hub/Linux/UEFI.
* **Тач в WoA так и не заработал.** В TWRP тач живой → железо целое.

---

## 5. Известные проблемы / долги

* **`ios16-root.img` пустой.** `mkiosroot.sh` сделал `mkfs.hfsplus` (16 ГиБ, 8192k журнал),
  затем `mount: unknown filesystem type 'hfsplus'` — в WSL нет ни модуля
  (`/lib/modules/6.18.54.1-microsoft-standard-WSL2`), ни строки в `/proc/filesystems`.
  Решение: поставить пакет **`hfsplus`** (hpmount/hpcopy) и наполнять образ без mount,
  либо монтировать образ на хосте/в другой VM. Для первого запуска XNU root **не нужен**.
* **apfs-fuse** собрался только с тремя фиксами (записать в NOTES, чтобы не повторять):
  `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`, `git submodule update --init --recursive`
  (иначе `No SOURCES given to target: lzfse`), и в `ApfsLib/PList.h` первой строкой
  `#include <cstdint>`.
* **Рабочее дерево `ios-cas` грязное**: ~40 файлов modified (весь `shim/`, `tools/`, 3 патча),
  плюс `AGENTS.md`. Ничего не закоммичено → при следующей CI-сборке это может разъехаться
  с локальным состоянием. Перед новой работой — `git diff` и осознанный коммит.
* **`AGENTS.md` в `ios-cas`** требует: читать `NOTES.md` перед стартом и **обновлять handoff
  в `NOTES.md` после каждого milestone**. Этого не делали с 22.10 23:41 — долг.
* Пользователь переключает агентов часто → handoff должен быть всегда актуален.
* Никаких `prebuilt/` в репозитории нет: ядро берётся **только** из CI-артефакта.

---

## 6. Ритуал работы с телефоном

* Восстановление: **TWRP** — Power + Vol Down. Пользователь много раз был «в тврп», это норма.
* Загрузка образа: `fastboot boot <img>` (не flash — `boot` не ломает разделы).
* Бэкапы, которые уже есть: `stock_boot_backup.img`, `stock_vbmeta_backup.img`,
  `Mu-cas-nopwr-backup.img`, `gpt_backup_sda.bin`.
* `vbmeta_disabled.img` — если понадобится отключить верификацию.
* Явный критерий «как понять, что образ мёртвый»: **даже кружок не появился, ребут через ~20 с**.

---

## 7. Промпт для следующего агента (скопировать)

> Прочитай `C:\ports\handoff_ios.md`, затем `C:\ports\ios-cas\NOTES.md` (первые 130 строк + §Next).
> Состояние: shim грузится на cas, прыжок в ядро проверен стабом, XNU собран CI
> (run `39995850227`, артефакт `xnu-kernel`). Первым делом: скачать артефакт и
> применить platform-match `xiaomi,cas` (патчи 0016/0018), затем `mkpayload.py` + `shim/build.sh`
> + `fastboot boot`. Телефон в fastboot/TWRP. Не трогать треки UEFI и HackiOS.
