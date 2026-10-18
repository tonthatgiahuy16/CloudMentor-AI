def validate_source_location(
    *,
    owner: str,
    page: int | None,
    line_range: tuple[int, int] | None,
    paragraph_range: tuple[int, int] | None,
) -> None:
    locations = (
        page,
        line_range,
        paragraph_range,
    )

    if (
        sum(
            location is not None
            for location in locations
        )
        != 1
    ):
        raise ValueError(
            f"{owner} must define exactly one "
            "source location"
        )

    if page is not None:
        if (
            not isinstance(page, int)
            or isinstance(page, bool)
            or page < 1
        ):
            raise ValueError(
                f"{owner} source locations must "
                "use positive ordered positions"
            )

        return

    source_range = (
        line_range
        if line_range is not None
        else paragraph_range
    )

    if (
        not isinstance(source_range, tuple)
        or len(source_range) != 2
    ):
        raise ValueError(
            f"{owner} source locations must "
            "use positive ordered positions"
        )

    start, end = source_range

    if (
        not isinstance(start, int)
        or isinstance(start, bool)
        or not isinstance(end, int)
        or isinstance(end, bool)
        or start < 1
        or end < start
    ):
        raise ValueError(
            f"{owner} source locations must "
            "use positive ordered positions"
        )
