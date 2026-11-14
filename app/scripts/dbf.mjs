// Minimal dBASE III reader (enough for the USGS/IAU gazetteer .dbf). No dependencies.
import { readFileSync } from 'node:fs';

export function readDbf(path) {
  const buf = readFileSync(path);
  const nRecords = buf.readUInt32LE(4);
  const headerLen = buf.readUInt16LE(8);
  const recordLen = buf.readUInt16LE(10);
  const fields = [];
  let off = 32;
  while (buf[off] !== 0x0d) {
    const name = buf.toString('latin1', off, off + 11).replace(/\0.*$/, '');
    fields.push({ name, type: String.fromCharCode(buf[off + 11]), len: buf[off + 16] });
    off += 32;
  }
  const dec = new TextDecoder('utf-8');
  const rows = [];
  for (let i = 0; i < nRecords; i++) {
    let p = headerLen + i * recordLen;
    if (buf[p] === 0x2a) continue; // deleted
    p += 1;
    const row = {};
    for (const f of fields) {
      const raw = dec.decode(buf.subarray(p, p + f.len)).trim();
      row[f.name] = f.type === 'N' || f.type === 'F' ? (raw === '' ? null : Number(raw)) : raw;
      p += f.len;
    }
    rows.push(row);
  }
  return { fields, rows };
}
