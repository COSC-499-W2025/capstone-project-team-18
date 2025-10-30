import sys
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
CLASSES_DIR = SRC_DIR / "classes"

for p in (str(CLASSES_DIR), str(SRC_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.classes.analyzer import CAnalyzer, TypeScriptAnalyzer  # type: ignore  # noqa: E402


def test_c_analyzer_functions_structs_typedefs_includes(tmp_path):
    c_code = '''
#include <stdio.h>
#include "myheader.h"

struct Point {
    int x;
    int y;
};

typedef struct Point Point_t;

typedef int myint;

void foo() {}
int bar(int a) { return a; }
'''
    c_file = tmp_path / "example.c"
    c_file.write_text(c_code)
    analyzer = CAnalyzer(str(c_file))
    report = analyzer.analyze()
    stats = report.statistics.to_dict()
    assert stats["NUMBER_OF_FUNCTIONS"] == 2
    assert stats["NUMBER_OF_STRUCTS"] == 1
    assert stats["NUMBER_OF_TYPEDEFS"] == 2
    assert stats["NUMBER_OF_INCLUDES"] == 2


def test_c_analyzer_empty_file(tmp_path):
    c_file = tmp_path / "empty.c"
    c_file.write_text("")
    analyzer = CAnalyzer(str(c_file))
    report = analyzer.analyze()
    stats = report.statistics.to_dict()
    assert stats["NUMBER_OF_FUNCTIONS"] == 0
    assert stats["NUMBER_OF_STRUCTS"] == 0
    assert stats["NUMBER_OF_TYPEDEFS"] == 0
    assert stats["NUMBER_OF_INCLUDES"] == 0


def test_typescript_analyzer_classes_interfaces_functions_imports(tmp_path):
    ts_code = '''
import React from "react";
import { something } from "./local";
import * as fs from "fs";

class MyClass {}
interface MyInterface {}

function foo() {}
const bar = () => {};
export function baz() {}
'''
    ts_file = tmp_path / "example.ts"
    ts_file.write_text(ts_code)
    analyzer = TypeScriptAnalyzer(str(ts_file))
    report = analyzer.analyze()
    stats = report.statistics.to_dict()
    assert stats["NUMBER_OF_CLASSES"] == 1
    assert stats["NUMBER_OF_INTERFACES"] == 1
    assert stats["NUMBER_OF_FUNCTIONS"] == 3
    assert "react" in stats["IMPORTED_PACKAGES"]
    assert "fs" in stats["IMPORTED_PACKAGES"]


def test_typescript_analyzer_empty_file(tmp_path):
    ts_file = tmp_path / "empty.ts"
    ts_file.write_text("")
    analyzer = TypeScriptAnalyzer(str(ts_file))
    report = analyzer.analyze()
    stats = report.statistics.to_dict()
    assert stats["NUMBER_OF_CLASSES"] == 0
    assert stats["NUMBER_OF_INTERFACES"] == 0
    assert stats["NUMBER_OF_FUNCTIONS"] == 0
    assert stats["IMPORTED_PACKAGES"] == []
