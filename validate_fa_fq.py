import sys
import gzip
import re
import argparse
from itertools import islice
from concurrent.futures import ThreadPoolExecutor, as_completed

VALID_SEQ_RE = re.compile(r"^[A-Za-z\-\.\~\*]+$")

def open_file(path):
    return gzip.open(path, 'rt') if path.endswith('.gz') else open(path)

# FASTQ: records are 4 lines
def parse_fastq(file):
    while True:
        lines = list(islice(file, 4))
        if not lines:
            break
        if len(lines) != 4:
            yield None, "Incomplete FASTQ record"
        else:
            yield lines, None

def validate_fastq_record(record):
    lines, err = record
    if err:
        return False, err
    h, s, p, q = [l.strip() for l in lines]
    if not h.startswith("@"):
        return False, "Missing '@' in header"
    if not p.startswith("+"):
        return False, "Missing '+' line"
    if len(s) != len(q):
        return False, "Sequence and quality lengths differ"
    return True, None

# FASTA: records start with '>'
def parse_fasta(file):
    records = []
    group = []
    for line in file:
        if line.startswith(">"):
            if group:
                records.append(group)
                group = []
        group.append(line)
    if group:
        records.append(group)
    return records

def validate_fasta_record(lines):
    header = lines[0].strip()
    if not header.startswith(">") or len(header) == 1:
        return False, "Invalid FASTA header"
    for seq_line in lines[1:]:
        seq = seq_line.strip()
        if not VALID_SEQ_RE.fullmatch(seq):
            return False, f"Invalid sequence line: '{seq}'"
    return True, None

def validate_file(filepath, filetype='auto', max_workers=4):
    try:
        with open_file(filepath) as f:
            first_line = f.readline()
            if filetype == 'auto':
                if first_line.startswith(">"):
                    filetype = 'fasta'
                elif first_line.startswith("@"):
                    filetype = 'fastq'
                else:
                    return False, "Unrecognized file format"
            f.seek(0)

            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                if filetype == 'fastq':
                    records = list(parse_fastq(f))
                    futures = [pool.submit(validate_fastq_record, rec) for rec in records]
                else:
                    records = parse_fasta(f)
                    futures = [pool.submit(validate_fasta_record, rec) for rec in records]

                for fut in as_completed(futures):
                    ok, err = fut.result()
                    if not ok:
                        return False, f"{filepath}: {err}"
        return True, f"{filepath}: Valid {filetype.upper()}"
    except Exception as e:
        return False, f"{filepath}: Exception: {e}"

def main():
    parser = argparse.ArgumentParser(description="Validate a FASTA or FASTQ file (optionally .gz)")
    parser.add_argument("file", help="Path to .fasta, .fastq, or .gz file")
    parser.add_argument("-t", "--threads", type=int, default=4, help="Number of threads (default: 4)")
    parser.add_argument("-f", "--type", choices=["fasta", "fastq", "auto"], default="auto", help="Force file type (default: auto)")

    args = parser.parse_args()
    ok, msg = validate_file(args.file, args.type, args.threads)
    print(f"[✓] {msg}" if ok else f"[×] {msg}")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
