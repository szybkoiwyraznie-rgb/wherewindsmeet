#!/usr/bin/env python3
"""Wspólna baza wiedzy i logika kontekstu cutscen (`text_msg`, `world_view_person_voice`, `audio`).

Moduł współdzielony przez `tools/buduj_czytanki.py` oraz `tools/buduj_paczke.py`,
aby czytanki i Pakiet dla Tłumacza miały spójne i sprawdzone rozpoznawanie mówców,
podział dużych ciągów napisów na sceny/regiony oraz odróżnianie przebrania gracza.
"""

from __future__ import annotations

from collections import defaultdict
import re

ZAKRES_PROLOG_TM = (590291, 590459)

_RE_ZN_INTERP = re.compile(r"[\s，。？！、：；“”‘’（）()\[\]…—\-,.?!:;'\"]+")

GENERYCZNE_NAZWY_GRACZA_ZH = frozenset({"玩家", "主角", "我", "你"})
GENERYCZNE_NAZWY_GRACZA_TXT = frozenset(
    {
        "player",
        "main character",
        "me",
        "gracz",
        "bohater",
        "bohaterka",
        "you xia",
    }
)

MOWCY_CUTSCEN_EN_IGNORUJ = frozenset({"The ancients said", "(Vocal expression", "Answer"})

# Jednoznaczne prefiksy w `text_msg` przed pojedynczą spacją
# (z wyłączeniem imion mogących być wołaczem w treści zdania)
MOWCY_CUTSCEN_ZH_NA_EN: dict[str, str] = {
    "我": "Me",
    "玩家": "Player",
    "主角": "Player",
    "师父": "Master",
    "众弟子": "Disciples",
    "行当管理员": "Profession Administrator",
    "玄元教教徒": "Xuanyuan Cultist",
    "李秀才": "Scholar Li",
    "刘大娘": "Aunt Liu",
    "聆杏村村长": "Apricot Village Chief",
    "客人": "Guest",
    "客人A": "Guest A",
    "客人B": "Guest B",
    "绣金楼男打手": "Aureate Pavilion Male Thug",
    "绣金楼女打手": "Aureate Pavilion Female Thug",
}

# Dodatkowe mapowanie chińskich imion wyłącznie do wyszukiwania tłumaczenia mówcy na polski / dwujęzyczną etykietę
MOWCY_CUTSCEN_ZH_DO_TLUMACZENIA: dict[str, str] = {
    "伊刀": "Yi Dao",
    "寒香寻": "Han Xiangxun",
    "江晏": "Jiang Yan",
    "江无浪": "Jiang Wulang",
    "陈子奚": "Chen Zixi",
    "千夜": "Qianye",
    "红线": "Ruby",
    "赵大哥": "Big Zhao",
    "多福": "Duofu",
    "丁乐成": "Ding Lecheng",
}

# Polskie odpowiedniki ról cutscen niemających osobnego wpisu encyklopedycznego w `index/`
MOWCY_ROLE_PL: dict[str, str] = {
    "Master": "Mistrz",
    "Disciples": "Uczniowie",
    "Profession Administrator": "Zarządca cechu",
    "Xuanyuan Cultist": "Wyznawca Kultu Xuanyuan",
    "Scholar Li": "Uczony Li",
    "Aunt Liu": "Ciotka Liu",
    "Apricot Village Chief": "Sołtys Wioski Morelowej",
    "Duofu": "Duofu",
    "Ding Lecheng": "Ding Lecheng",
    "Guest": "Gość",
    "Guest A": "Gość A",
    "Guest B": "Gość B",
    "Anxi Army": "Żołnierz Armii Anxi",
    "Aureate Pavilion Male Thug": "Zbir Złotego Pawilonu",
    "Aureate Pavilion Female Thug": "Bandytka Złotego Pawilonu",
}

ZNANE_IMIONA_CUTSCEN_EN = frozenset(
    {
        "Yi Dao",
        "Han Xiangxun",
        "Ruby",
        "Jiang Yan",
        "Jiang Wulang",
        "Chen Zixi",
        "Qianye",
        "Big Zhao",
    }
)

# Dopasowanie prefiksów `audio` (dłuższe / bardziej szczegółowe zawsze przed ogólnymi!)
VO_DOMENY: list[tuple[str, str, str, int | None, tuple[int, ...]]] = [
    ("vo_xinshou", "PROLOG_WOZ", "Prolog — nocny powóz: Jiang Yan i Chen Zixi", None, ()),
    ("vo_xsfb", "PROLOG_WOZ", "Prolog — nocny powóz: Jiang Yan i Chen Zixi", None, ()),
    ("vo_sm_xsm9p3", "PROLOG_ZASADZKA", "Prolog — zasadzka w ulewie i Nefryt Zhenguan", None, ()),
    ("vo_sm_xsm9p4", "QH_POLIGON_TY", "Qinghe — poligon Tian Yinga", None, ()),
    ("vo_sm_xs", "PROLOG_ZASADZKA", "Prolog — zasadzka w ulewie i Nefryt Zhenguan", None, ()),
    ("vo_sm_sxdm4_cs_wnyf", "QH_POKOJ_HAN", "Qinghe — pokój Han Xiangxun", 1, (30185,)),
    ("vo_sm_sxdm4_cs_zlxl", "QH_BAMBUS_RUBY", "Qinghe (Bambusowy Gaj) — przebudzenie z Ruby", 1, (30161,)),
    ("vo_sm_sxdm4_cs_xhyd", "QH_BLISSFUL", "Qinghe — zasadzka i wrobienie Yi Dao", 1, (30188,)),
    ("vo_gp_bxxdg", "QH_PODZIEMIA", "Qinghe — podziemia pod gospodą", 1, ()),
    ("vo_shenxiandu", "QH_BLISSFUL", "Qinghe — gospoda i Rozdział I", 1, ()),
    ("vo_sm_sxd", "QH_BLISSFUL", "Qinghe — gospoda i Rozdział I", 1, ()),
    ("vo_tianzai", "QH_APRICOT", "Qinghe — Wioska Morelowa i Kult Xuanyuan", None, ()),
    ("vo_ss_tq_cs_dtgt", "QH_TQ", "Qinghe (Studnia Niebios) — rada starszych i sprawa rodu Xie", None, ()),
    ("vo_ss_tq_cs_hyrzzfnr", "QH_TQ", "Qinghe (Studnia Niebios) — konfrontacja w sekcie", None, ()),
    ("vo_ss_tq_cs_mygdh", "QH_TQ", "Qinghe (Studnia Niebios) — rozmowa o Feng Buyu", None, ()),
    ("vo_tianquan", "QH_TQ", "Qinghe (Studnia Niebios) — rada starszych i sprawa rodu Xie", None, ()),
    ("vo_ss_tq", "QH_TQ_SPRAWA", "Qinghe (Studnia Niebios)", None, ()),
    ("vo_gp_qhptkh", "QH_YE_WANSHAN", "Qinghe — Generał Ye Wanshan i najazd Kitanów", None, (30182,)),
    ("vo_gp_qhfgd", "QH_TIAN_YING", "Qinghe — Szczyt Halo i rozkaz Tian Yinga", None, ()),
    ("vo_ss_yyry", "QH_POLIGON_TY", "Qinghe — poligon Tian Yinga", None, ()),
    ("vo_gp_yyry", "QH_POLIGON_TY", "Qinghe — poligon Tian Yinga", None, ()),
    ("vo_ss_axnzgz", "QH_POBOCZNE", "Qinghe — Nanzhu / Południowy księżyc", None, ()),
    ("vo_sm_qhmzbxxm8", "QH_POBOCZNE", "Qinghe — wątki poboczne", None, ()),
    ("vo_ss_qhsj", "QH_POBOCZNE", "Qinghe — wątki poboczne", None, ()),
    ("vo_ss_qhyxd", "QH_BLISSFUL", "Qinghe — finał Rozdziału I", 1, (30376, 30377)),
    ("vo_ss_qhjz", "KAIFENG_POBOCZNE", "Kaifeng — skazaniec i straż", 4, ()),
    ("vo_gp_jmc", "KAIFENG_JMC", "Kaifeng — Basen Jinming (Jinming Pool)", None, ()),
    ("vo_ss_zszdm8p2", "KAIFENG_JMC", "Kaifeng — Basen Jinming (wspomnienia)", None, ()),
    ("vo_ss_qjsjm8p2", "KAIFENG_JMC", "Kaifeng — Basen Jinming", None, ()),
    ("vo_gp_zhyfhdym7", "KAIFENG_JMC", "Kaifeng — Basen Jinming (punkt obserwacyjny Ruolan)", None, ()),
    ("vo_gp_wswll", "KAIFENG_FIVE_RATS", "Kaifeng — pościg po dachach (Pięć Szczurów)", 4, ()),
    ("vo_gp_glwswll", "KAIFENG_FIVE_RATS", "Kaifeng — pościg po dachach (Pięć Szczurów)", 4, ()),
    ("vo_amb_glwswll", "KAIFENG_FIVE_RATS", "Kaifeng — po pościgu po dachach", 4, ()),
    ("vo_gp_bjshgz", "KAIFENG_FIVE_RATS", "Kaifeng — pościg po dachach", 4, ()),
    ("vo_sm_bjsp", "KAIFENG_FIVE_RATS", "Kaifeng — pościg po dachach", 4, ()),
    ("vo_sm_kfm7", "KAIFENG_GLOWNE", "Kaifeng — Rozdział II", 4, ()),
    ("vo_sm_kfm8", "KAIFENG_GLOWNE", "Kaifeng — Rozdział II", 4, ()),
    ("vo_gp_ggjy", "KAIFENG_GLOWNE", "Kaifeng — tajna komnata i skarb", 4, ()),
    ("vo_gp_dyrl", "KAIFENG_GLOWNE", "Kaifeng — Piec Prawości", 4, ()),
    ("vo_sm_kfdyrl", "KAIFENG_GLOWNE", "Kaifeng — Piec Prawości", 4, ()),
    ("vo_ss_wcwm", "KAIFENG_GLOWNE", "Kaifeng — zbrojownia i spór o dziedzictwo", 4, ()),
    ("vo_gp_xjwcwm", "KAIFENG_GLOWNE", "Kaifeng — zbrojownia", 4, ()),
    ("vo_gp_dazswll", "KAIFENG_GLOWNE", "Kaifeng — Piec Prawości", 4, ()),
    ("vo_gp_cpczs", "KAIFENG_GLOWNE", "Kaifeng — północny Kaifeng", 4, ()),
    ("vo_gp_tslzs", "KAIFENG_RZEKA", "Kaifeng — powrót Mistrza Rzeki", None, ()),
    ("vo_ss_yyps", "KAIFENG_DUCHY", "Kaifeng — Złoty Liść i opowieści miasta", None, ()),
    ("vo_ss_hcjy", "KAIFENG_VELVET", "Kaifeng — Velvet Shade / Posłaniec Kwiatów", None, ()),
    ("vo_ss_jlzy", "KAIFENG_NINEWAYS", "Kaifeng — Dziewięć Dróg (Nine Mortal Ways)", None, ()),
    ("vo_sm_hxzx", "HEXI_ANXI", "Hexi — Przełęcz Bramy Nefrytowej i Armia Anxi", 6, ()),
    ("vo_gp_btczs", "HEXI_ANXI", "Hexi — Armia Anxi", 6, ()),
    ("vo_gp_ymgzs", "HEXI_ANXI", "Hexi — Armia Anxi", 6, ()),
    ("vo_gp_hxzsbtc", "HEXI_ANXI", "Hexi — Armia Anxi", 6, ()),
    ("vo_gp_ptjm11p3", "HEXI_PTJ", "Hexi — krwawa uczta (Aynur i księżyc)", 6, ()),
    ("vo_ss_cjlzm11p2", "HEXI_PTJ", "Hexi — poszukiwania Maojie", 6, ()),
    ("vo_gp_zychca", "HEXI_ANXI", "Hexi — Generał Zhang Yichao i powrót do Tang", 6, ()),
    ("vo_ss_lzsl", "HEXI_ANXI", "Hexi — Generał Zhang Yichao i powrót do Tang", 6, ()),
    ("vo_sm_hxp2lzq", "HEXI_LIANGZHOU", "Hexi — Melodia Liangzhou", 6, ()),
    ("vo_sm_hxp3zyl", "HEXI_PAPIEROWY_KSIEZYC", "Hexi — Księżyc z Papieru", 6, ()),
    ("vo_gp_xzzs", "HEXI_BANQUET", "Hexi — uczta i przysięga ostrza", 7, ()),
    ("vo_ss_lyax", "HEXI_FIN", "Hexi — epilog", 7, ()),
    ("vo_ai_b_", "BOSS_WYZWANIA", "Wyzwania i starcia z bossami", None, ()),
    ("vo_gp_wydzs", "BOSS_WYZWANIA", "Wyzwania Jianghu", None, ()),
]

# Sprawdzone w `index/` granice pod-scen wewnątrz spójnych bloków `text_msg` (ID początkowe -> (tytuł, grupa_id, powiązane_cutsceny, notka))
KOTWICE_SCEN_TM: dict[int, tuple[str, int | None, tuple[int, ...], str]] = {
    590000: ("Qinghe (Studnia Niebios) — przysięga uczniów", None, (), ""),
    590011: ("Qinghe — ucieczka z Bambusowej Wioski", 1, (), ""),
    590016: ("Qinghe — przybycie do Bambusowej Wioski", 1, (), ""),
    590021: ("Świat gry — przysięga Gildii Uzdrowicieli", None, (), ""),
    590025: ("Świat gry — kronika ścieżek Uczonego i Medyka", None, (), ""),
    590050: ("Świat gry — próba lekkości i wyzwanie na niebie", None, (), ""),
    590058: ("Qinghe — walka Yi Dao z Aureate Pavilion i Qianye (przysięga trzech pucharów)", 1, (30377,), ""),
    590148: ("Qinghe — Generał Ye Wanshan i najazd Kitanów", None, (30182,), ""),
    590188: ("Qinghe — gwar przed gospodą w Rozdziale I", 1, (), ""),
    590208: ("Qinghe — gospoda Cioci Han i Qianye (wersja filmowa bez prefiksów)", 1, (30166, 30167), "Wariant filmowy sceny z gospody (por. napisy 590230–590250)."),
    590216: ("Qinghe — trening Tai Chi i biały niedźwiedź", None, (), ""),
    590225: ("Qinghe — pisanie listu do Cioci Han", 1, (30177,), ""),
    590230: ("Qinghe — gospoda Cioci Han, Parting Tears i Qianye", 1, (30166, 30167), ""),
    590251: ("Qinghe — powrót pod gospodę i rozmowa z Ciocią Han po ataku", 1, (), ""),
    590266: ("Qinghe — rozmowa Yi Dao i Han Xiangxun o Chu Qingquanie i Kaifengu", 1, (), ""),
    590282: ("Qinghe — gospoda Cioci Han (krótka wersja napisowa)", 1, (30166,), "Krótki wariant sceny z gospody."),
    590291: ("Qinghe — gospoda Cioci Han (wariant napisowy)", 1, (30166,), "Wariant napisowy początku spotkania w gospodzie (por. 590248–590250)."),
    590296: ("Qinghe — oblężenie Aureate Pavilion i skrzynka do Kaifengu", 1, (30178, 30413), ""),
    590314: ("Qinghe — incydent z Paniczem Qu i słowa Cioci Han", 1, (), ""),
    590321: ("Prolog — nocna podróż powozem: Jiang Yan (Jiang Wulang) i Chen Zixi", None, (), "Otwierający filmowy dialog w nocnym powozie (wraz z wizytówką Jiang Yana)."),
    590336: ("Prolog — zasadzka w ulewie i pościg o Nefryt Zhenguan", None, (), "Kontynuacja filmowego Prologu: nocna ucieczka z niemowlęciem i Nefrytem Zhenguan."),
    590352: ("Qinghe — przepisywanie ksiąg u Cioci Han i rozmowa o Yi Dao", 1, (30207,), ""),
    590373: ("Qinghe — przebudzenie w podziemiach", 1, (), ""),
    590376: ("Qinghe — pożar gospody, poświęcenie Ruby i starcie z Qianye", 1, (30413, 30374, 30375), ""),
    590432: ("Qinghe (Iluzja Qianye) — pożegnanie Yi Dao i przebudzenie w Bambusowym Gaju", 1, (30376, 30377, 30161), ""),
    590457: ("Wstawka miejska — spokój w mieście", None, (), ""),
    591487: ("Warianty i powtórki napisów (Prolog, Qinghe, Five Rats, Kaifeng)", None, (), "Alternatywne / późniejsze warianty napisów do wcześniejszych scen fabularnych."),
}


def norm_cut_zh(text: str) -> str:
    return _RE_ZN_INTERP.sub("", text or "")


def wvpv_pid(vid: str, encyklopedia: dict[int, dict]) -> int | None:
    if not vid.isdigit():
        return None
    iv = int(vid)
    if iv >= 100000 and iv % 100 == 0 and (iv // 100000) in encyklopedia:
        return iv // 100000
    if (iv // 1000) in encyklopedia:
        return iv // 1000
    if (iv // 100) in encyklopedia:
        return iv // 100
    return None


def dopasuj_domene_vo(audio: str) -> tuple[str, str, int | None, tuple[int, ...]] | None:
    aud = (audio or "").lower()
    if not aud or aud.startswith("func_"):
        return None
    for pref, dom, tytul, gid, cuts in VO_DOMENY:
        if aud.startswith(pref):
            return (dom, tytul, gid, cuts)
    return None


def bezposredni_mowca_en(row: dict, zh: str, en_txt: str, *, ignoruj_audio: bool = False) -> str | None:
    if not ignoruj_audio:
        aud = row.get("audio") or ""
        if "_npc_" not in aud and any(
            tok in aud for tok in ("_player_m_", "_player_f_", "_pma_", "_pfa_", "_zhujue_", "_zjnan_")
        ):
            return "You Xia"
        if aud.startswith("vo_xinshou_jwl_"):
            return "Jiang Yan"
        if aud.startswith(("vo_xinshou_ly_", "vo_xsfb_liyu_")):
            return "Chen Zixi"
        if "_cs_zlxl_hx_" in aud:
            return "Ruby"
        if "_cs_xhyd_yd_" in aud or "_cs_wnyf_yd_" in aud:
            return "Yi Dao"
        if "_cs_mygdh_fby_" in aud:
            return "Feng Buyu"
        if "_cs_fgdws_ty_" in aud:
            return "Tian Ying"

    men = (row.get("mowca_en") or "").strip()
    if men and men not in MOWCY_CUTSCEN_EN_IGNORUJ and "(" not in men:
        if men in ("Me", "Player", "Main Character"):
            return "You Xia"
        return men

    m_en = re.match(r"^([A-Za-z][A-Za-z0-9 '\-]{0,30}):\s+(.+)$", (en_txt or "").strip())
    if m_en:
        pref = m_en.group(1).strip()
        if pref in ("Me", "Player"):
            return "You Xia"
        if pref in MOWCY_ROLE_PL or pref in ZNANE_IMIONA_CUTSCEN_EN:
            return pref

    zh_s = (zh or "").strip()
    m_zh = re.match(r"^([^\s]+) (.+)$", zh_s)
    if m_zh and m_zh.group(1) in MOWCY_CUTSCEN_ZH_NA_EN and not m_zh.group(2).startswith(" "):
        if m_zh.group(1) == "我" and zh_s.startswith("我 我"):
            return None
        mapped = MOWCY_CUTSCEN_ZH_NA_EN[m_zh.group(1)]
        return "You Xia" if mapped in ("Me", "Player") else mapped
    return None


def zbuduj_indeksy_mowcow(
    ix,
    wvpv_raw: dict[str, str],
    encyklopedia_po_id: dict[int, dict],
) -> tuple[dict[str, str], dict[str, str], list[tuple[str, str]]]:
    """Zbuduj słowniki mówców na podstawie `world_view_person_voice` oraz powtórzeń z `text_msg`."""
    kandydaci: dict[str, set[str]] = defaultdict(set)
    wvpv_dokladne: dict[str, set[str]] = defaultdict(set)

    for vid, zh_txt in wvpv_raw.items():
        pid = wvpv_pid(vid, encyklopedia_po_id)
        if pid is None:
            continue
        entry = encyklopedia_po_id.get(pid)
        if not entry or not entry.get("nazwa"):
            continue
        en_name = (ix.en(entry["nazwa"]) or "").strip()
        if not en_name:
            continue
        nz = norm_cut_zh(zh_txt)
        if len(nz) >= 6:
            wvpv_dokladne[nz].add(en_name)
            kandydaci[nz].add(en_name)
        for czesc in re.split(r"[\n。？！；]+", zh_txt):
            nc = norm_cut_zh(czesc)
            if len(nc) >= 8:
                kandydaci[nc].add(en_name)

    for row in ix.cutsceny_kontekst.get("napis", ()):
        kl = row.get("k")
        if kl not in ix.teksty:
            continue
        sp = bezposredni_mowca_en(row, ix.teksty[kl].zrodlo, ix.en(kl) or "")
        if not sp:
            continue
        zh = ix.teksty[kl].zrodlo.strip()
        nz = norm_cut_zh(zh)
        if len(nz) >= 6:
            kandydaci[nz].add(sp)
        m_zh = re.match(r"^([^\s]+) (.+)$", zh)
        if m_zh and m_zh.group(1) in MOWCY_CUTSCEN_ZH_NA_EN and not m_zh.group(2).startswith(" "):
            nt = norm_cut_zh(m_zh.group(2))
            if len(nt) >= 6:
                kandydaci[nt].add(sp)

    glos_wvpv_dokladny = {
        nz: next(iter(sps)) for nz, sps in wvpv_dokladne.items() if len(sps) == 1
    }
    mowca_napisow_exact = {
        nz: next(iter(sps)) for nz, sps in kandydaci.items() if len(sps) == 1
    }
    mowca_napisow_dlugie = [
        (nz, next(iter(sps)))
        for nz, sps in kandydaci.items()
        if len(sps) == 1 and len(nz) >= 8
    ]
    return glos_wvpv_dokladny, mowca_napisow_exact, mowca_napisow_dlugie


def rozwiaz_mowce_en(
    row: dict,
    zh: str,
    en_raw: str,
    glos_wvpv_dokladny: dict[str, str],
    mowca_napisow_exact: dict[str, str],
    mowca_napisow_dlugie: list[tuple[str, str]],
    *,
    ignoruj_audio: bool = False,
) -> str | None:
    sp_en = bezposredni_mowca_en(row, zh, en_raw, ignoruj_audio=ignoruj_audio)
    if sp_en:
        return sp_en
    nz = norm_cut_zh(zh)
    sp_en = glos_wvpv_dokladny.get(nz)
    if sp_en or ignoruj_audio:
        return sp_en
    sp_en = mowca_napisow_exact.get(nz)
    if not sp_en and len(nz) >= 8:
        found: set[str] = set()
        for cand_nz, cand_sp in mowca_napisow_dlugie:
            if nz in cand_nz or cand_nz in nz:
                found.add(cand_sp)
                if len(found) > 1:
                    break
        if len(found) == 1:
            sp_en = next(iter(found))
    return sp_en


def wyczysc_prefiks_mowcy(txt: str, sp_en: str | None, mowca_out: str | None) -> tuple[str, str | None, bool]:
    """Usuń zduplikowany prefiks `Ktoś: treść` z napisu i zwróć (oczyszczony_tekst, ewent_sp_en, czy_gracz)."""
    cleaned_txt = txt
    detected_sp = sp_en
    czy_gracz = sp_en == "You Xia"
    m_colon = re.match(r"^([A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż0-9 '\-]{1,32}):\s+(.+)$", txt.strip())
    if m_colon:
        pref = m_colon.group(1).strip()
        rest = m_colon.group(2).strip()
        known_prefs = {"Me", "Player", "Ja", "You Xia", *MOWCY_ROLE_PL.keys(), *MOWCY_ROLE_PL.values()}
        if (
            pref in known_prefs
            or (sp_en and pref.lower() == sp_en.lower())
            or (mowca_out and pref.lower() == mowca_out.lower())
            or pref in ZNANE_IMIONA_CUTSCEN_EN
        ):
            cleaned_txt = rest
            if not detected_sp:
                if pref in ("Me", "Player", "Ja", "You Xia"):
                    detected_sp = "You Xia"
                    czy_gracz = True
                else:
                    detected_sp = pref
    return cleaned_txt, detected_sp, czy_gracz


def wykryj_plec_napisow(napisy: list[dict], teksty: dict) -> dict[int, str]:
    """Wykryj sąsiednie pary wariantów męski/żeński (`bohater` / `bohaterka`) w `text_msg`."""
    plec_wiersza: dict[int, str] = {}
    for idx in range(len(napisy) - 1):
        a, b = napisy[idx], napisy[idx + 1]
        if b["wiersz"] != a["wiersz"] + 1:
            continue
        ta, tb = teksty[a["k"]], teksty[b["k"]]
        aud_a, aud_b = a.get("audio") or "", b.get("audio") or ""
        is_mf_zh = any(
            (p1 in ta.zrodlo and p2 in tb.zrodlo)
            for p1, p2 in (("小子", "小妮子"), ("少侠", "女侠"), ("小妮子", "小子"), ("女侠", "少侠"))
        )
        is_mf_aud = ("_m_" in aud_a and "_f_" in aud_b) or ("_pma_" in aud_a and "_pfa_" in aud_b)
        if is_mf_zh or is_mf_aud:
            if any(x in ta.zrodlo for x in ("小妮子", "女侠")) or "_f_" in aud_a or "_pfa_" in aud_a:
                plec_wiersza[a["wiersz"]] = "bohaterka"
                plec_wiersza[b["wiersz"]] = "bohater"
            else:
                plec_wiersza[a["wiersz"]] = "bohater"
                plec_wiersza[b["wiersz"]] = "bohaterka"
    return plec_wiersza


def segmentuj_ciag_napisow(ciag: list[dict]) -> list[dict]:
    """Podziel ciągły blok `text_msg` na logiczne pod-sceny z metadanymi kontekstowymi."""
    if len(ciag) < 10:
        return [
            {
                "rows": ciag,
                "tytul": "",
                "grupa": None,
                "cuts": (),
                "notka": "",
                "wygladzono_audio": set(),
            }
        ]

    raw = [dopasuj_domene_vo(r.get("audio") or "") for r in ciag]
    n = len(ciag)
    ma_kompana: list[bool] = [False] * n
    for i, d in enumerate(raw):
        if d is None:
            continue
        wi = ciag[i]["wiersz"]
        for j in range(max(0, i - 25), min(n, i + 26)):
            if j != i and raw[j] is not None and raw[j][0] == d[0] and abs(ciag[j]["wiersz"] - wi) <= 25:
                ma_kompana[i] = True
                break

    smooth = list(raw)
    wygladzono_audio: set[int] = set()
    for i, d in enumerate(raw):
        if d is None or ma_kompana[i]:
            continue
        w = ciag[i]["wiersz"]
        prev_d = None
        for j in range(i - 1, -1, -1):
            if w - ciag[j]["wiersz"] > 35:
                break
            if raw[j] is not None and ma_kompana[j]:
                prev_d = raw[j]
                break
        next_d = None
        for j in range(i + 1, n):
            if ciag[j]["wiersz"] - w > 35:
                break
            if raw[j] is not None and ma_kompana[j]:
                next_d = raw[j]
                break
        if prev_d and next_d and prev_d[0] == next_d[0] and prev_d[0] != d[0]:
            smooth[i] = prev_d
            wygladzono_audio.add(w)

    wynik: list[dict] = []
    cur_rows: list[dict] = []
    cur_dom: str | None = None
    cur_tytul = ""
    cur_grupa: int | None = None
    cur_cuts: tuple[int, ...] = ()
    cur_notka = ""

    def flush() -> None:
        if not cur_rows:
            return
        wynik.append(
            {
                "rows": list(cur_rows),
                "tytul": cur_tytul,
                "grupa": cur_grupa,
                "cuts": cur_cuts,
                "notka": cur_notka,
                "wygladzono_audio": wygladzono_audio,
            }
        )

    for i, r in enumerate(ciag):
        w = r["wiersz"]
        d = smooth[i]
        anchor = KOTWICE_SCEN_TM.get(w)
        split = False
        if not cur_rows:
            split = True
        elif anchor is not None:
            split = True
        elif d is not None and cur_dom is not None and d[0] != cur_dom:
            in_locked_span = (590296 <= w <= 590372) or (590376 <= w <= 590456)
            if not in_locked_span:
                split = True

        if split:
            flush()
            cur_rows = [r]
            if anchor is not None:
                cur_tytul, cur_grupa, cur_cuts, cur_notka = anchor
                cur_dom = d[0] if d else None
            elif d is not None:
                cur_dom, cur_tytul, cur_grupa, cur_cuts = d
                cur_notka = ""
            else:
                cur_dom = None
                cur_tytul = ""
                cur_grupa = None
                cur_cuts = ()
                cur_notka = ""
        else:
            cur_rows.append(r)
            if cur_dom is None and d is not None:
                cur_dom = d[0]
                if not cur_tytul:
                    cur_tytul = d[1]
                if cur_grupa is None:
                    cur_grupa = d[2]
                if not cur_cuts:
                    cur_cuts = d[3]
            elif d is not None and d[3] and not cur_cuts:
                cur_cuts = d[3]

    flush()
    return wynik
