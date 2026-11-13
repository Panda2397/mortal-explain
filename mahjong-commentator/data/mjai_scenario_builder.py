#!/usr/bin/env python3
"""Interactive MJAI JSONL scenario builder for a four-player kyoku.

Supports draws, discards, calls, kans, riichi, and wins. It can also be stopped
at any point to create a partial decision-test fixture.
"""

import json
import re
from collections import Counter
from pathlib import Path

TILE = re.compile(r"(?:[1-9][mps]|5[mps]r|[ESWNPFC]|\?)\Z")
RED = {"5mr", "5pr", "5sr"}


def tile_type(tile):
    return tile[:2] if tile in RED else tile


def ask_int(prompt, default, low, high):
    while True:
        value = input(f"{prompt} [{default}]: ").strip()
        try:
            n = int(value) if value else default
            if low <= n <= high:
                return n
        except ValueError:
            pass
        print(f"Enter a number from {low} to {high}.")


def ask_tile(prompt, allow_unknown=False):
    while True:
        tile = input(prompt).strip()
        if TILE.fullmatch(tile) and (allow_unknown or tile != "?"):
            return tile
        print("Use 1m..9m, 1p..9p, 1s..9s, E S W N P F C, 5mr/5pr/5sr" + (", or ?" if allow_unknown else "") + ".")


def ask_yes_no(prompt, default=False):
    while True:
        s = input(f"{prompt} [{'Y/n' if default else 'y/N'}]: ").strip().lower()
        if not s:
            return default
        if s in ("y", "yes"):
            return True
        if s in ("n", "no"):
            return False
        print("Enter y or n.")


def ask_choice(prompt, choices, default):
    choices = tuple(choices)
    while True:
        value = input(f"{prompt} [{default}]: ").strip().lower() or default
        matches = [choice for choice in choices if choice.startswith(value)]
        if value in choices:
            return value
        if len(matches) == 1:
            return matches[0]
        print("Choose one of: " + ", ".join(choices) + ".")


def ask_tiles(prompt, count):
    while True:
        tiles = input(prompt).replace(",", " ").split()
        if len(tiles) == count and all(TILE.fullmatch(tile) and tile != "?" for tile in tiles):
            return tiles
        print(f"Enter exactly {count} valid, space-separated tiles.")


def ask_four_ints(prompt, default=None):
    while True:
        suffix = f" [{' '.join(map(str, default))}]" if default is not None else ""
        raw = input(f"{prompt}{suffix}: ").strip()
        if not raw and default is not None:
            return default.copy()
        try:
            values = [int(value) for value in raw.replace(",", " ").split()]
        except ValueError:
            values = []
        if len(values) == 4:
            return values
        print(f"Enter exactly 4 integers; received {len(values)}/4.")


def ask_optional_tiles(prompt):
    while True:
        raw = input(prompt).strip()
        if not raw:
            return []
        tiles = raw.replace(",", " ").split()
        invalid = [tile for tile in tiles if not TILE.fullmatch(tile) or tile == "?"]
        if not invalid:
            return tiles
        print("Invalid tile(s): " + ", ".join(invalid) + ".")


def show_hands(hands, names, current_actor=None):
    print("\nCurrent hands:")
    for seat, hand in enumerate(hands):
        marker = " ->" if seat == current_actor else "   "
        shown = " ".join(hand) if hand is not None else "(hidden)"
        print(f"{marker} P{seat} {names[seat]}: {shown}")


def remove_from_hand(hand, tiles, actor):
    if hand is None:
        return True
    candidate = hand.copy()
    for tile in tiles:
        if tile not in candidate:
            print(f"Player {actor} cannot use {tile}: hand is {' '.join(hand)}")
            return False
        candidate.remove(tile)
    hand[:] = candidate
    return True


def read_hora(actor, target):
    """Read the result fields used by game_001.json's hora events."""
    deltas = ask_four_ints("  Score deltas", [0, 0, 0, 0])
    ura_markers = ask_optional_tiles("  Ura indicators (space-separated; blank for none): ")
    return {"type": "hora", "actor": actor, "target": target,
            "deltas": deltas, "ura_markers": ura_markers}


def add_visible(counter, exact_red, tile):
    """Record a distinct physical tile seen in a known hand/draw/discard."""
    if tile == "?":
        return
    kind = tile_type(tile)
    if counter[kind] >= 4:
        raise ValueError(f"{tile} would make {counter[kind] + 1}/4 copies of {kind}.")
    if tile in RED and tile in exact_red:
        raise ValueError(f"Duplicate red five {tile}.")
    counter[kind] += 1
    if tile in RED:
        exact_red.add(tile)


def read_hand(actor, counter, exact_red):
    while True:
        s = input(f"Player {actor} starting 13 tiles (space-separated; '?' for hidden) : ").strip()
        if s == "?":
            return None
        hand = s.replace(",", " ").split()
        print(f"Player {actor}: received {len(hand)}/13 tiles.")
        invalid = [tile for tile in hand if not TILE.fullmatch(tile) or tile == "?"]
        if invalid:
            print("Invalid tile(s): " + ", ".join(invalid) + ".")
            print("Use 1m..9m, 1p..9p, 1s..9s, E S W N P F C, or 5mr/5pr/5sr.")
            continue
        if len(hand) != 13:
            missing = 13 - len(hand)
            if missing > 0:
                print(f"Add {missing} more tile(s), or enter a single '?' for a hidden hand.")
            else:
                print(f"Remove {-missing} tile(s); a starting hand must contain 13.")
            continue
        candidate = counter.copy()
        reds = exact_red.copy()
        try:
            for tile in hand:
                add_visible(candidate, reds, tile)
        except ValueError as err:
            print(err)
            continue
        counter.clear()
        counter.update(candidate)
        exact_red.clear()
        exact_red.update(reds)
        return hand


def main():
    print("MJAI scenario builder - 4 players, one kyoku")
    print("Notation: 4m=manzu, 4p=pinzu, 4s=souzu, P=white, F=green, C=red, 5pr=red 5p")
    print("Seats 0,1,2,3 are in turn order starting from dealer (oya).")
    output = input("Output filename [custom.mjai.jsonl]: ").strip() or "custom.mjai.jsonl"
    names_str = input("Player names (comma-separated, blank for P0..P3): ").strip()
    names = [n.strip() for n in names_str.split(",")] if names_str else [f"P{i}" for i in range(4)]
    if len(names) != 4:
        print("Expected 4 names; using P0..P3.")
        names = [f"P{i}" for i in range(4)]
    oya = ask_int("Dealer seat (oya)", 0, 0, 3)
    while True:
        bakaze = (input("Round wind [E] (E/S/W/N): ").strip() or "E").upper()
        if bakaze in "ESWN" and len(bakaze) == 1:
            break
        print("Enter E, S, W or N.")
    kyoku = ask_int("Kyoku number", 1, 1, 4)
    honba = ask_int("Honba", 0, 0, 99)
    kyotaku = ask_int("Kyotaku (riichi sticks)", 0, 0, 99)
    scores = ask_four_ints("Four scores", [25000, 25000, 25000, 25000])

    counter, exact_red = Counter(), set()
    while True:
        dora = ask_tile("Initial dora indicator: ")
        try:
            add_visible(counter, exact_red, dora)
            break
        except ValueError as err:
            print(err)

    hands = [read_hand(i, counter, exact_red) for i in range(4)]
    events = [
        {"type": "start_game"},
        {"type": "start_kyoku", "bakaze": bakaze, "kyoku": kyoku,
         "honba": honba, "kyotaku": kyotaku, "oya": oya,
         "scores": scores, "dora_marker": dora,
         "tehais": [h[:] if h is not None else ["?"] * 13 for h in hands]},
    ]

    print("\nEnter actions in play order. Type 'done' at a draw prompt to save a partial round.")
    actor, action_count = oya, 0
    terminal = False
    while True:
        show_hands(hands, names, actor)
        print(f"\nPlayer {actor} ({names[actor]}) - action {action_count + 1}")
        raw_draw = input("  Draw tile ('?' if hidden, 'done' to save): ").strip()
        if raw_draw.lower() == "done":
            break
        if not TILE.fullmatch(raw_draw):
            print("Invalid draw tile. Try again.")
            continue
        if hands[actor] is not None and raw_draw == "?":
            print("A tracked hand needs a known draw to validate future discards.")
            continue
        if hands[actor] is not None:
            print("  Hand after draw: " + " ".join(hands[actor] + [raw_draw]))
        else:
            print(f"  Hand after draw: (hidden), drew {raw_draw}")
        self_action = ask_choice(
            "  Action (discard/reach/ankan/kakan/hora)",
            ("discard", "reach", "ankan", "kakan", "hora"), "discard")
        if self_action == "hora":
            events.extend([
                {"type": "tsumo", "actor": actor, "pai": raw_draw},
                read_hora(actor, actor),
                {"type": "end_kyoku"},
            ])
            terminal = True
            break
        if self_action in ("ankan", "kakan"):
            count = 4 if self_action == "ankan" else 3
            consumed = ask_tiles(f"  Consumed tiles ({count}): ", count)
            check_hand = hands[actor][:] + [raw_draw] if hands[actor] is not None else None
            pai = None if self_action == "ankan" else ask_tile("  Added kan tile: ")
            removed = consumed if self_action == "ankan" else [pai]
            if not remove_from_hand(check_hand, removed, actor):
                continue
            if hands[actor] is not None:
                hands[actor] = check_hand
            kan_event = {"type": self_action, "actor": actor, "consumed": consumed}
            if pai is not None:
                kan_event["pai"] = pai
            events.extend([{"type": "tsumo", "actor": actor, "pai": raw_draw}, kan_event])
            if ask_yes_no("  Reveal a new dora indicator?"):
                marker = ask_tile("  New dora indicator: ")
                events.append({"type": "dora", "dora_marker": marker})
            action_count += 1
            continue
        discard = ask_tile("  Discard tile: ")

        # Determine tsumogiri (whether the physically drawn copy was discarded).
        if raw_draw == discard or raw_draw == "?":
            if hands[actor] is not None and discard == raw_draw and discard not in hands[actor]:
                tsumogiri = True
            else:
                tsumogiri = ask_yes_no("  Was the drawn tile discarded (tsumogiri)?", raw_draw == discard)
        else:
            tsumogiri = False
        if tsumogiri and raw_draw != "?" and discard != raw_draw:
            print("Cannot tsumogiri a tile different from the known draw.")
            continue

        if hands[actor] is not None:
            candidates = hands[actor][:] + [raw_draw]
            if discard not in candidates:
                print(f"Cannot discard {discard}: not in player {actor}'s tracked hand.")
                continue
            if not tsumogiri and discard not in hands[actor]:
                print("Non-tsumogiri discard must come from the original 13 tiles.")
                continue

        candidate_counts, candidate_reds = counter.copy(), exact_red.copy()
        try:
            if raw_draw != "?":
                add_visible(candidate_counts, candidate_reds, raw_draw)
            if hands[actor] is None and not (raw_draw == discard and tsumogiri):
                # The tile was hidden until it appeared in the discard pond.
                add_visible(candidate_counts, candidate_reds, discard)
        except ValueError as err:
            print(f"Invalid physical tile count: {err}")
            continue

        counter, exact_red = candidate_counts, candidate_reds
        if hands[actor] is not None:
            if not tsumogiri:
                hands[actor].remove(discard)
                hands[actor].append(raw_draw)
            # else drawn tile is discarded; hand stays unchanged

        events.append({"type": "tsumo", "actor": actor, "pai": raw_draw})
        if self_action == "reach":
            events.append({"type": "reach", "actor": actor})
        events.append({"type": "dahai", "actor": actor, "pai": discard, "tsumogiri": tsumogiri})
        if self_action == "reach":
            events.append({"type": "reach_accepted", "actor": actor})
        action_count += 1
        reaction = ask_choice(
            "  Reaction (none/chi/pon/daiminkan/hora)",
            ("none", "chi", "pon", "daiminkan", "hora"), "none")
        if reaction == "none":
            actor = (actor + 1) % 4
            continue
        caller = ask_int("  Calling/winning player", (actor + 1) % 4, 0, 3)
        if caller == actor:
            print("A player cannot call their own discard; reaction ignored.")
            actor = (actor + 1) % 4
            continue
        if reaction == "hora":
            events.extend([read_hora(caller, actor), {"type": "end_kyoku"}])
            terminal = True
            break
        if reaction == "chi" and caller != (actor + 1) % 4:
            print("Chi is only legal for the next player; reaction ignored.")
            actor = (actor + 1) % 4
            continue
        count = 2 if reaction in ("chi", "pon") else 3
        consumed = ask_tiles(f"  Consumed tiles ({count}): ", count)
        if not remove_from_hand(hands[caller], consumed, caller):
            actor = (actor + 1) % 4
            continue
        events.append({"type": reaction, "actor": caller, "target": actor,
                       "pai": discard, "consumed": consumed})
        action_count += 1
        actor = caller
        if reaction == "daiminkan":
            continue
        show_hands(hands, names, actor)
        call_discard = ask_tile("  Discard after call: ")
        if hands[actor] is not None and call_discard not in hands[actor]:
            print(f"Cannot discard {call_discard}; stopping after the call.")
            break
        if hands[actor] is not None:
            hands[actor].remove(call_discard)
        events.append({"type": "dahai", "actor": actor, "pai": call_discard, "tsumogiri": False})
        action_count += 1
        actor = (actor + 1) % 4

    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for event in events:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    print(f"Saved {len(events)} MJAI events ({action_count} actions) to {path.resolve()}")
    print("The kyoku ended with hora." if terminal else "Saved a partial single-kyoku log.")


if __name__ == "__main__":
    try:
        main()
    except (EOFError, KeyboardInterrupt):
        print("\nInterrupted. No file written (use 'done' to save).")
