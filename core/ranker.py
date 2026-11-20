"""Metadata-driven deterministic ranking, independent of JSON storage order."""
def score(entry,context):
    exact=context.command==entry["command"].split(" ",1)[0]
    priority=entry.get("context_priority",50) if exact else entry.get("root_priority",50)
    return (-priority,-entry.get("learning_value",50),len(entry["command"]),entry["id"])
