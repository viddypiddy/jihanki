from jihanki.pipeline.output import find_files


def test_find_files_comprehensive(test_file_structure):
    """Test find_files with specific file, wildcard by extension at root, and recursive with multiple extensions"""

    # Test 1: Specific file
    result = find_files(["file1.txt"], test_file_structure)
    assert sorted(result) == ["file1.txt"]

    # Test 2: Wildcard by extension at root
    result = find_files(["*.py"], test_file_structure)
    assert sorted(result) == ["file2.py"]

    # Test 3: Recursive with multiple extensions
    result = find_files(["**/*.txt", "**/*.py"], test_file_structure)
    expected = [
        "file1.txt",
        "file2.py",
        "subdir1/nested1.txt",
        "subdir1/nested1.py",
        "subdir2/nested2.txt",
        "subdir1/deepdir/deep1.txt",
        "subdir1/deepdir/deep1.py",
        "subdir1/deepdir/verydeep/very1.txt",
    ]
    assert sorted(result) == sorted(expected)

    # Test 4: Wildcarding in explicit deep directory
    result = find_files(["subdir1/deepdir/*.*"], test_file_structure)
    expected = ["subdir1/deepdir/deep1.txt", "subdir1/deepdir/deep1.py"]
    assert sorted(result) == sorted(expected)
