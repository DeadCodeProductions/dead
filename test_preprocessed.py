import preprocessing


def test_extern_removal() -> None:
    with open("./gcc_preprocessed_code.c", "r") as f:
        lines = f.read().split("\n")

    with open("./preprocessed_oracle.c", "r") as f:
        oracle = f.read()
    assert oracle == preprocessing.preprocess_lines(lines).strip()
