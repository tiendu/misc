import ast
import os
import argparse
import csv
from abc import ABC, abstractmethod
from typing import List, Dict


# --- Models ---

class FunctionInfo:
    def __init__(self, script: str, name: str, args: str, returns: str, deps: str):
        self.script = script
        self.name = name
        self.args = args
        self.returns = returns
        self.deps = deps

    def as_dict(self) -> Dict[str, str]:
        return {
            'Script Name': self.script,
            'Function Name': self.name,
            'Args': self.args,
            'Returns': self.returns,
            'Dependencies': self.deps
        }


# --- Analyzer ---

class ScriptAnalyzer:
    def __init__(self, script_path: str):
        self.script_path = script_path

    def analyze(self) -> List[FunctionInfo]:
        with open(self.script_path, 'r') as file:
            tree = ast.parse(file.read(), self.script_path)

        functions = []
        imports = {alias.name.split('.')[0] for node in ast.walk(tree)
                   if isinstance(node, (ast.Import, ast.ImportFrom))
                   for alias in node.names}

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                name = node.name
                args = ', '.join(arg.arg for arg in node.args.args)
                returns = 'None' if node.returns is None else ast.dump(node.returns)
                deps = {
                    sub.func.id for sub in ast.walk(node)
                    if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name)
                    and sub.func.id in imports
                }.union({
                    sub.func.value.id for sub in ast.walk(node)
                    if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute)
                    and isinstance(sub.func.value, ast.Name)
                    and sub.func.value.id in imports
                })

                functions.append(FunctionInfo(
                    script=os.path.basename(self.script_path),
                    name=name,
                    args=args,
                    returns=returns,
                    deps=', '.join(sorted(deps))
                ))
        return functions


# --- Report Generation ---

class ReportGenerator:
    def __init__(self, directory: str):
        self.directory = directory

    def generate(self) -> List[FunctionInfo]:
        report = []
        for fname in os.listdir(self.directory):
            if fname.endswith('.py'):
                analyzer = ScriptAnalyzer(os.path.join(self.directory, fname))
                report.extend(analyzer.analyze())
        return report


# --- Reporting Abstraction ---

class Reporter(ABC):
    @abstractmethod
    def output(self, data: List[FunctionInfo]) -> None:
        pass


class ConsoleReporter(Reporter):
    def __init__(self, col_widths=None):
        self.col_widths = col_widths or {
            'Script Name': 20, 'Function Name': 25, 'Args': 40,
            'Returns': 100, 'Dependencies': 15
        }

    def truncate(self, text: str, width: int) -> str:
        return text if len(text) <= width else text[:width - 3] + '...'

    def output(self, data: List[FunctionInfo]) -> None:
        headers = self.col_widths.keys()
        header = "| " + " | ".join(self.truncate(h, self.col_widths[h]) for h in headers) + " |"
        divider = "|" + "|".join('-' * self.col_widths[h] for h in headers) + "|"

        print(header)
        print(divider)
        for row in data:
            print("| " + " | ".join(
                self.truncate(getattr(row, attr.lower().replace(' ', '_')), self.col_widths[col])
                for col, attr in zip(headers, row.as_dict().keys())
            ) + " |")


class CSVReporter(Reporter):
    def __init__(self, path: str):
        self.path = path

    def output(self, data: List[FunctionInfo]) -> None:
        with open(self.path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(data[0].as_dict().keys()))
            writer.writeheader()
            for row in data:
                writer.writerow(row.as_dict())


class MarkdownReporter(Reporter):
    def __init__(self, path: str):
        self.path = path

    def _calc_widths(self, rows: List[FunctionInfo]) -> Dict[str, int]:
        headers = list(rows[0].as_dict().keys())
        return {
            h: max(len(h), max(len(r.as_dict()[h]) for r in rows))
            for h in headers
        }

    def output(self, data: List[FunctionInfo]) -> None:
        widths = self._calc_widths(data)
        headers = list(data[0].as_dict().keys())

        with open(self.path, 'w') as f:
            f.write("| " + " | ".join(h.ljust(widths[h]) for h in headers) + " |\n")
            f.write("|" + "|".join('-' * (widths[h] + 2) for h in headers) + "|\n")
            for row in data:
                f.write("| " + " | ".join(row.as_dict()[h].ljust(widths[h]) for h in headers) + " |\n")


# --- Main CLI Entry ---

def main():
    parser = argparse.ArgumentParser(description="Analyze Python scripts and report function signatures.")
    parser.add_argument('-d', '--directory', required=True, help='Directory of Python files')
    parser.add_argument('-o', '--output', required=True, help='Path to output CSV file')
    parser.add_argument('-m', '--markdown', help='Path to output Markdown file')
    args = parser.parse_args()

    if not os.path.isdir(args.directory):
        print(f"❌ Error: Directory {args.directory} does not exist.")
        return

    report = ReportGenerator(args.directory).generate()
    if not report:
        print("⚠️  No Python functions found.")
        return

    ConsoleReporter().output(report)
    CSVReporter(args.output).output(report)

    if args.markdown:
        MarkdownReporter(args.markdown).output(report)


if __name__ == '__main__':
    main()
