"""Recognize table rebuilds in an SQL trace by the identity of the tables involved."""
import re

TOKEN = re.compile(r"'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"|`[^`]*`|\[[^]]*\]|--[^\n]*|/\*[\s\S]*?\*/|[\w$]+|[^\s]")
CLASSIFIER = "copy-drop"


def recorded_rebuild(trace):
    """The rule behind the rebuild flags of results without a rebuild_classifier field.

    It accepts any CREATE TABLE together with any DROP TABLE, related or not.
    """
    return bool(re.search(r'\b(?:CREATE (?:TEMPORARY |TEMP )?TABLE)\b', trace, re.I)
                and re.search(r'\bDROP TABLE\b', trace, re.I))


def split(sql):
    """Token lists per statement; a trigger body stays inside its CREATE TRIGGER."""
    current, trigger = [], False
    for token in TOKEN.findall(sql):
        if token.startswith(("--", "/*")):
            continue
        if token != ";":
            current.append(token)
            if not trigger and token.lower() == "trigger" and current[0].lower() == "create" and len(current) <= 3:
                trigger = True
            continue
        if trigger and current[-1].lower() != "end":
            current.append(token)
            continue
        if current:
            yield current
        current, trigger = [], False
    if current:
        yield current


def name(token):
    return (token[1:-1] if token[0] in '"`[' else token).lower()


def table(tokens, index):
    """Table name at index, without a schema qualifier, and the index after it."""
    if tokens[index + 1:index + 2] == ["."]:
        index += 2
    return name(tokens[index]), index + 1


def sources(tokens, words, start):
    for index in range(start, len(words) - 1):
        if words[index] in ("from", "join") and tokens[index + 1] != "(":
            yield table(tokens, index + 1)[0]


def events(sql):
    for tokens in split(sql):
        words = [t.lower() for t in tokens]
        try:
            if words[0] == "create":
                index = 2 if words[1] in ("temp", "temporary") else 1
                if words[index] != "table":
                    continue
                if words[index + 1:index + 4] == ["if", "not", "exists"]:
                    index += 3
                target, after = table(tokens, index + 1)
                yield "create", target
                if words[after:after + 1] == ["as"]:
                    for source in sources(tokens, words, after):
                        yield "copy", source, target
            elif words[:2] == ["drop", "table"]:
                index = 4 if words[2:4] == ["if", "exists"] else 2
                yield "drop", table(tokens, index)[0]
            elif words[:2] == ["alter", "table"]:
                old, after = table(tokens, 2)
                if words[after:after + 2] == ["rename", "to"]:
                    yield "rename", old, table(tokens, after + 2)[0]
            elif words[0] in ("insert", "replace") and "into" in words:
                target, after = table(tokens, words.index("into") + 1)
                if "select" in words[after:]:
                    for source in sources(tokens, words, after):
                        yield "copy", source, target
        except IndexError:
            continue


def rebuilt_tables(sql):
    """Tables whose rows were copied into a table created in this SQL and which were then dropped.

    This covers the replacement sequence (create, copy, drop, rename) and the
    holding-table sequence (copy out, drop, recreate, copy back). A failing
    execution counts once it reaches the DROP of the copied table.
    """
    identity, copied, rebuilt = {}, set(), []
    for event in events(sql):
        if event[0] == "create":
            identity[event[1]] = None
        elif event[0] == "rename":
            identity[event[2]] = identity.pop(event[1], event[1])
        elif event[0] == "copy":
            source = identity.get(event[1], event[1])
            if source is not None and event[2] in identity and identity[event[2]] is None:
                copied.add(source)
        else:
            original = identity.pop(event[1], event[1])
            if original in copied and original not in rebuilt:
                rebuilt.append(original)
    return rebuilt


def rebuild(sql):
    return bool(rebuilt_tables(sql))
