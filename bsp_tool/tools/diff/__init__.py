"""Run with 64-bit python! Respawn .bsp files are large!"""
import difflib
import itertools
import os
import re
from typing import Iterable

from ... import RespawnBsp
from ...branches.respawn import titanfall, titanfall2


shared_maps = [("mp_angel_city", "mp_angel_city"),
               ("mp_colony", "mp_colony02"),
               ("mp_relic", "mp_relic02"),
               ("mp_rise", "mp_rise"),
               ("mp_wargames", "mp_wargames")]
# ^ r1 map name, r2 map name


def diff_respawn_bsps(bsp1, bsp2, full=False):
    for i in range(128):
        lump1 = bsp1.branch.LUMP(i).name
        lump2 = bsp2.branch.LUMP(i).name
        bsp1_header = bsp1.HEADERS[lump1]
        bsp2_header = bsp2.HEADERS[lump2]

        if bsp1_header.length == 0 and bsp2_header.length == 0:
            continue  # skip empty lumps

        print(f"{bsp1.branch.LUMP(i).name}", end="  ")
        print("Y" if bsp1_header.offset == bsp2_header.offset else "N", end="")
        print("Y" if bsp1_header.length == bsp2_header.length else "N", end="")
        print("Y" if bsp1_header.version == bsp2_header.version else "N", end="")
        print("Y" if bsp1_header.fourCC == bsp2_header.fourCC else "N", end="  ")

        try:
            lump_1_contents = bsp1.lump_as_bytes(lump1)
            lump_2_contents = bsp2.lump_as_bytes(lump2)
        except Exception:
            print("????")  # couldn't load a lump, unsure which
            # TODO: handle edge case where one bsp has the lump, and the other does not
            continue  # skip this lump

        lumps_match = (lump_1_contents == lump_2_contents)
        print("YES!" if lumps_match else "NOPE")
        if full:
            # diff lumps
            if not lumps_match:
                # TODO: measure the scale of the differences
                if lump1 in bsp1.branch.LUMP_CLASSES and lump2 in bsp2.branch.LUMP_CLASSES:
                    difflib.unified_diff([lc.__repr__() for lc in getattr(bsp1, lump1)],
                                         [lc.__repr__() for lc in getattr(bsp2, lump2)],
                                         f"{bsp1.filename}.{lump1}", f"{bsp1.filename}.{lump1}")
                elif lump1 == "ENTIITES":
                    diff_entities(bsp1, bsp2)
                elif lump1 == "PAKFILE":
                    diff_pakfiles(bsp1, bsp2)
                else:
                    diff = difflib.diff_bytes(difflib.unified_diff,
                                              [*split(lump_1_contents, 32)], [*split(lump_2_contents, 32)],
                                              f"{bsp1.filename}.{lump1}".encode(), f"{bsp1.filename}.{lump1}".encode())
                    print(*diff, sep="\n")
                    pass

    for ent_file in ["ENTITIES_env", "ENTITIES_fx", "ENTITIES_script", "ENTITIES_snd", "ENTITIES_spawn"]:
        print(ent_file, end="  ")
        print("YES!" if getattr(bsp1, ent_file) == getattr(bsp1, ent_file) else "NOPE")


def diff_entities(bsp1: RespawnBsp, bsp2: RespawnBsp):
    for i, e1, e2 in zip(itertools.count(), bsp1.ENTITIES, bsp2.ENTITIES):
        if e1 != e2:
            print(f"Entity #{i}")
            print("  {")
            for k1, k2, v1, v2 in zip(e1.keys(), e2.keys(), e1.values(), e2.values()):
                if v1 != v2:
                    print(f'-     "{k1}" "{v1}"')
                    print(f'+     "{k2}" "{v2}"')
                else:
                    print(f'      "{k1}" "{v1}"')
            print("  }")


def diff_pakfiles(bsp1: RespawnBsp, bsp2: RespawnBsp):
    pak1_files = bsp1.PAKFILE.namelist()
    pak2_files = bsp2.PAKFILE.namelist()
    for filename in pak1_files:
        if filename not in pak2_files:
            print(f"- {filename}")
        else:
            print(f"  {filename}")
            # compare sizes with .PAKFILE.getinfo("filename").file_size
            # compare file hashes?
    for filename in pak2_files:
        if filename not in pak1_files:
            print(f"+ {filename}")


def dump_headers(maplist):
    for r1_filename, r2_filename in maplist:
        # if not os.path.exists(f"E:/Mod/TitanfallOnline/maps/{r1_filename}.bsp"):
        #     continue  # need to test r1o maps against r1
        print(r1_filename.upper())

        r1o_map_exists = os.path.exists(f"E:/Mod/TitanfallOnline/maps/{r1_filename}.bsp")

        r1_map = RespawnBsp(titanfall, f"E:/Mod/Titanfall/maps/{r1_filename}.bsp")
        if r1o_map_exists:
            r1o_map = RespawnBsp(titanfall, f"E:/Mod/TitanfallOnline/maps/{r1_filename}.bsp")
        r2_map = RespawnBsp(titanfall2, f"E:/Mod/Titanfall2/maps/{r2_filename}.bsp")

        for i in range(128):
            r1_lump = titanfall.LUMP(i)
            r2_lump = titanfall2.LUMP(i)

            r1_header = r1_map.HEADERS[r1_lump.name]
            if r1o_map_exists:
                r1o_header = r1o_map.HEADERS[r1_lump.name]
                r1o_header_length = r1o_header.length
            else:
                r1o_header_length = 0
            r2_header = r2_map.HEADERS[r2_lump.name]
            if (r1_header.length, r1o_header_length, r2_header.length) == (0, 0, 0):
                continue  # skip empty lumps
            print(r1_lump.name)
            print(f"{r1_lump.value:04X}  {r1_lump.name}")
            print(f"{'r1':<8}", r1_header)
            if r1o_map_exists:
                print(f"{'r1o':<8}", r1o_header)
            print(f"{'r2':<8}", r2_header)

        del r1_map, r2_map
        if r1o_map_exists:
            del r1o_map
        print("=" * 80)


def split(iterable: Iterable, chunk_size: int) -> Iterable:
    for i, _ in enumerate(iterable[::chunk_size]):
        yield iterable[i * chunk_size:(i + 1) * chunk_size]


def xxd(data: bytes, width: int = 32) -> str:
    """based on the linux hex editor"""
    # TODO: start index and length to read
    for i, _bytes in split(data, width):
        address = f"0x{i * width:08X}"
        hex = " ".join([f"{b:02X}" for b in _bytes])
        ascii = "".join([chr(b) if re.match(r"[a-zA-Z0-9/\\]", chr(b)) else "." for b in _bytes])
        yield f"{address}:  {hex}  {ascii}"


if __name__ == "__main__":
    # r1_relic = RespawnBsp(titanfall, "E:/Mod/Titanfall/maps/mp_relic.bsp")
    # r1o_relic = RespawnBsp(titanfall, "E:/Mod/TitanfallOnline/maps/mp_relic.bsp")
    # r2_relic = RespawnBsp(titanfall2, "E:/Mod/Titanfall2/maps/mp_relic02.bsp")
    # diff_respawn_bsps(r1_relic, r1o_relic)  # IDENTICAL!

    # r1_angel = RespawnBsp(titanfall, "E:/Mod/Titanfall/maps/mp_angel_city.bsp")
    # r1o_angel = RespawnBsp(titanfall, "E:/Mod/TitanfallOnline/maps/mp_angel_city.bsp")
    # r2_angel = RespawnBsp(titanfall2, "E:/Mod/Titanfall2/maps/mp_angel_city.bsp")
    # diff_respawn_bsps(r1_angel, r1o_angel)  # slight differences! interesting!

    dump_headers(shared_maps)
