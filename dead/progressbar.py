from typing import Iterable, TypeVar, cast

try:
    from tqdm import tqdm  # type:ignore
except ImportError:
    tqdm = None


T = TypeVar("T")


def progressbar(i: Iterable[T], desc: str, total: int | None = None) -> Iterable[T]:
    if tqdm:
        return cast(
            Iterable[T],
            tqdm(i, dynamic_ncols=True, leave=False, desc=desc, total=total),
        )
    return i
