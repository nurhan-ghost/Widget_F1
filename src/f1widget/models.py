"""API-independent standings and championship calculations."""
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Entry:
    identity: str
    position: int
    code: str
    name: str
    team_id: str
    team: str
    points: Decimal
    movement: int | None
    number: str | None = None


def parse_entries(table: dict, mode: str, previous: dict | None = None) -> list[Entry]:
    key = "DriverStandings" if mode == "drivers" else "ConstructorStandings"
    entity = "Driver" if mode == "drivers" else "Constructor"
    id_key = "driverId" if mode == "drivers" else "constructorId"
    old = {r[entity][id_key]: int(r["position"]) for r in (previous or {}).get(key, [])}
    entries = []
    for row in table.get(key, []):
        person = row[entity]
        identity = person[id_key]
        team = (row.get("Constructors") or [{}])[-1] if mode == "drivers" else person
        name = f"{person.get('givenName', '')} {person.get('familyName', '')}".strip() if mode == "drivers" else person["name"]
        code = person.get("code") or person.get("familyName", person.get("name", "???"))[:3].upper()
        position = int(row["position"])
        entries.append(Entry(identity, position, code, name, team.get("constructorId", ""),
                             team.get("name", "Unknown"), Decimal(row["points"]),
                             old[identity] - position if identity in old else None,
                             person.get("permanentNumber") if mode == "drivers" else None))
    return sorted(entries, key=lambda entry: entry.position)


def gap(points: Decimal, leader: Decimal) -> str:
    return "—" if points == leader else f"−{leader - points:g}"
