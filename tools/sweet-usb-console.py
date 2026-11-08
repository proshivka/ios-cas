#!/usr/bin/env python3
"""Collect the opt-in CAS XNU CDC ACM console on a Windows/Linux/macOS host.

Requires pyserial3.5. Only the unique diagnostic VID/PID/serial is selected.
The exact sweetlogid marker must be received before attributing a capture.
This tool reads console bytes; it does not send shell or reboot commands.
"""

from __future__ import annotations

import argparse
import codecs
import hashlib
import json
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

VID, PID, SERIAL = 0x1209, 0x0001, '0001'


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def choose_port(ports: Iterable[Any]) -> Any | None:
    matches = [port for port in ports if (port.vid, port.pid, port.serial_number) == (VID, PID, SERIAL)]
    if len(matches) > 1:
        raise RuntimeError('Multiple matching XNU console ports; retain diagnostics and select the physical target')
    return matches[0] if matches else None


def write_status(path: Path, record: dict[str, Any]) -> None:
    temporary = path.with_name(path.name + '.tmp-' + uuid.uuid4().hex)
    temporary.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8', newline='\n')
    temporary.replace(path)


def collect(marker: str, stem: Path, wait_seconds: int, capture_seconds: int) -> dict[str, Any]:
    import serial
    from serial.tools import list_ports

    if re.fullmatch(r'sweetlogid=[0-9a-f]{16}', marker) is None:
        raise ValueError('Expected an exact16-hex-digit sweetlogid marker')
    if not 1 <= wait_seconds <= 7200 or not 1 <= capture_seconds <= 7200:
        raise ValueError('Wait/capture durations must be between one second and two hours')
    stem.parent.mkdir(parents=True, exist_ok=True)
    raw_path = Path(str(stem) + '.bin')
    text_path = Path(str(stem) + '.txt')
    status_path = Path(str(stem) + '.json')
    if any(path.exists() for path in (raw_path, text_path, status_path)):
        raise RuntimeError('Console output already exists; choose a fresh capture stem')
    record: dict[str, Any] = {'Status': 'WAITING_FOR_CDC_ACM', 'StartedUtc': now(),
                              'ExpectedImageMarker': marker, 'RawPath': str(raw_path),
                              'TextPath': str(text_path), 'ConsoleBytes': 0,
                              'ImageMarkerSeen': False, 'ConsoleProfileSeen': False,
                              'HostPortOpened': False, 'UsbHardwareVerified': False,
                              'WaitSeconds': wait_seconds, 'CaptureSeconds': capture_seconds}
    write_status(status_path, record)
    deadline = time.monotonic() + wait_seconds
    stream = None
    while time.monotonic() < deadline:
        port = choose_port(list_ports.comports())
        if port is not None:
            try:
                stream = serial.Serial(port.device, baudrate=115200, timeout=0.5,
                                       write_timeout=1, xonxoff=False, rtscts=False, dsrdtr=False)
                record.update(Status='CDC_ACM_PORT_OPENED', HostPortOpened=True,
                              Port=port.device, PortDescription=port.description, ConnectedUtc=now())
                break
            except serial.SerialException as error:
                record['LastOpenError'] = str(error)
        record['CheckedUtc'] = now()
        write_status(status_path, record)
        time.sleep(0.5)
    if stream is None:
        record.update(Status='CDC_ACM_WAIT_EXPIRED', CompletedUtc=now())
        write_status(status_path, record)
        return record
    digest = hashlib.sha256()
    decoder = codecs.getincrementaldecoder('utf-8')('replace')
    window = b''
    deadline = time.monotonic() + capture_seconds
    last_status = 0.0
    try:
        with stream, raw_path.open('xb') as raw, text_path.open('x', encoding='utf-8', newline='') as text:
            while time.monotonic() < deadline:
                try:
                    chunk = stream.read(4096)
                except serial.SerialException as error:
                    record['ReadEnded'] = str(error)
                    break
                if chunk:
                    raw.write(chunk)
                    digest.update(chunk)
                    text.write(decoder.decode(chunk))
                    record['ConsoleBytes'] += len(chunk)
                    window = (window + chunk)[-131072:]
                    record['ImageMarkerSeen'] |= marker.encode('ascii') in window
                    record['ConsoleProfileSeen'] |= b'SWEET USB: CDC ACM console profile started' in window
                    record['UsbHardwareVerified'] = bool(record['ImageMarkerSeen'] and record['ConsoleProfileSeen'])
                    record['LastDataUtc'] = now()
                    if record['ConsoleBytes'] >= 128 * 1024 * 1024:
                        record['ReadEnded'] = 'Bounded128MiB capture limit reached'
                        break
                if time.monotonic() - last_status >= 5:
                    raw.flush(); text.flush()
                    record.update(Status='CDC_ACM_STREAM_ATTRIBUTED' if record['UsbHardwareVerified']
                                  else 'CDC_ACM_STREAM_ATTRIBUTION_PENDING', CheckedUtc=now())
                    write_status(status_path, record)
                    last_status = time.monotonic()
            text.write(decoder.decode(b'', final=True))
    finally:
        stream.close()
    record.update(Status='CDC_ACM_CAPTURED_WITH_IMAGE_MARKER' if record['UsbHardwareVerified']
                  else 'CDC_ACM_CAPTURED_UNATTRIBUTED', CompletedUtc=now(), RawSha256=digest.hexdigest())
    write_status(status_path, record)
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--marker', required=True)
    parser.add_argument('--output-stem', type=Path, required=True)
    parser.add_argument('--wait-seconds', type=int, default=1800)
    parser.add_argument('--capture-seconds', type=int, default=180)
    args = parser.parse_args()
    print(json.dumps(collect(args.marker, args.output_stem, args.wait_seconds, args.capture_seconds), indent=2))


if __name__ == '__main__':
    main()
