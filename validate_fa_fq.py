import sys
import gzip
from concurrent.futures import ThreadPoolExecutor, as_completed
from os.path import basename

def open_file(filepath):
    return gzip.open(filepath, "rt") if filepath.endswith(".gz") else open(filepath, "r")

def validate_fasta(filepath):
    try:
        with open_file(filepath) as f:
            header_seen = False
            for i, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                if line.startswith(">"):
                    if len(line) == 1:
                        return False, f"{filepath}: Empty FASTA header at line {i}"
                    header_seen = True
                else:
                    if not header_seen:
                        return False, f"{filepath}: Missing FASTA header before line {i}"
        return True, f"{filepath}: Valid FASTA"
    except Exception as e:
        return False, f"{filepath}: Exception during FASTA validation: {e}"

def validate_fastq(filepath):
    try:
        with open_file(filepath) as f:
            line_num = 0
            while True:
                header = f.readline()
                if not header:
                    break
                seq = f.readline()
                plus = f.readline()
                qual = f.readline()
                line_num += 4

                if not (seq and plus and qual):
                    return False, f"{filepath}: Incomplete FASTQ record ending at line {line_num}"

                if not header.startswith("@"):
                    return False, f"{filepath}: Expected '@' at line {line_num - 3}"
                if not plus.startswith("+"):
                    return False, f"{filepath}: Expected '+' at line {line_num - 1}"
                if len(seq.strip()) != len(qual.strip()):
                    return False, f"{filepath}: Sequence and quality lengths differ at line {line_num - 2}"
        return True, f"{filepath}: Valid FASTQ"
    except Exception as e:
        return False, f"{filepath}: Exception during FASTQ validation: {e}"

def detect_and_validate(filepath):
    try:
        with open_file(filepath) as f:
            for line in f:
                if line.startswith(">"):
                    return validate_fasta(filepath)
                elif line.startswith("@"):
                    return validate_fastq(filepath)
                elif not line.strip():
                    continue
                else:
                    break
        return False, f"{filepath}: Unknown or malformed file format"
    except Exception as e:
        return False, f"{filepath}: Could not open or read file: {e}"

def main(filepaths, max_workers=4):
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(detect_and_validate, fp): fp for fp in filepaths}
        for future in as_completed(futures):
            ok, msg = future.result()
            print(f"[✓] {msg}" if ok else f"[×] {msg}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        script_name = basename(sys.argv[0])
        print(f"Usage: python {script_name} <file1.fa|fq[.gz]> [file2.fa|fq[.gz]] ...")
        sys.exit(1)
    main(sys.argv[1:])
