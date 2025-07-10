import sys
import gzip
import argparse
import re
from itertools import islice

VALID_SEQ_RE = re.compile(r"^[A-Za-z\-\.\~\*]+$")  # FASTA allowed chars

def open_file(path):
    return gzip.open(path, 'rt') if path.endswith('.gz') else open(path)

def validate_fastq(filepath):
    try:
        with open_file(filepath) as f:
            lineno = 0
            while True:
                lines = list(islice(f, 4))
                if not lines:
                    break
                lineno += 4
                if len(lines) != 4:
                    return False, f"{filepath}: Incomplete FASTQ record near line {lineno}"
                h, s, p, q = [l.strip() for l in lines]
                if not h.startswith("@"):
                    return False, f"{filepath}: FASTQ header missing '@' at line {lineno - 3}"
                if not p.startswith("+"):
                    return False, f"{filepath}: FASTQ '+' line missing at line {lineno - 1}"
                if len(s) != len(q):
                    return False, f"{filepath}: Sequence and quality length mismatch at line {lineno - 2}"
        return True, f"{filepath}: Valid FASTQ"
    except Exception as e:
        return False, f"{filepath}: Error reading FASTQ: {e}"

def validate_fasta(filepath):
    try:
        with open_file(filepath) as f:
            lineno = 0
            header_seen = False
            for line in f:
                lineno += 1
                line = line.strip()
                if not line:
                    continue
                if line.startswith(">"):
                    if len(line) == 1:
                        return False, f"{filepath}: Empty FASTA header at line {lineno}"
                    header_seen = True
                else:
                    if not header_seen:
                        return False, f"{filepath}: Sequence found before any header at line {lineno}"
                    if not VALID_SEQ_RE.fullmatch(line):
                        return False, f"{filepath}: Invalid characters in sequence at line {lineno}"
        return True, f"{filepath}: Valid FASTA"
    except Exception as e:
        return False, f"{filepath}: Error reading FASTA: {e}"

def detect_format(filepath):
    with open_file(filepath) as f:
        for line in f:
            if line.startswith(">"):
                return "fasta"
            elif line.startswith("@"):
                return "fastq"
            elif not line.strip():
                continue
            else:
                break
    return "unknown"

def validate_file(filepath, filetype):
    if filetype == "auto":
        filetype = detect_format(filepath)
        if filetype == "unknown":
            return False, f"{filepath}: Could not detect file type"
    if filetype == "fasta":
        return validate_fasta(filepath)
    elif filetype == "fastq":
        return validate_fastq(filepath)
    else:
        return False, f"{filepath}: Invalid file type specified"

def main():
    parser = argparse.ArgumentParser(description="Validate FASTA/FASTQ file (streaming, low-memory)")
    parser.add_argument("file", help="Path to FASTA/FASTQ file (optionally .gz)")
    parser.add_argument("-f", "--type", choices=["fasta", "fastq", "auto"], default="auto",
                        help="Force file type: fasta, fastq, or auto (default: auto)")
    args = parser.parse_args()

    ok, msg = validate_file(args.file, args.type)
    print(f"[✓] {msg}" if ok else f"[×] {msg}")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
