"""Tactical analysis module for World Cup 2026 matchups.

Defines tactical profiles for all 48 World Cup teams and provides
matchup analysis functions that compare playing styles, identify
mismatches, and produce human-readable tactical breakdowns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ── Tactical Profile Dataclass ──────────────────────────────────────────────


@dataclass(frozen=True)
class TacticalProfile:
    """Tactical identity of a national team."""

    team: str
    playing_style: str  # possession, counter_attack, high_press, defensive_block, direct, wing_play
    formation_preference: str  # 4-3-3, 4-4-2, 3-5-2, 4-2-3-1, 5-3-2, etc.
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    key_player: str = ""
    coach_style_summary: str = ""
    fifa_rank: int = 50  # approximate


# ── Style Matchup Matrix ────────────────────────────────────────────────────

# Maps (style_home, style_away) → base tactical advantage for home team.
# Positive = favours home, negative = favours away.
_STYLE_MATCHUP: dict[tuple[str, str], float] = {
    # High press vs defensive block: press teams struggle to break through, but
    # defensive teams offer little counter threat — slight home edge if home presses.
    ("high_press", "defensive_block"): 0.15,
    ("defensive_block", "high_press"): -0.05,
    # Possession vs counter-attack: possession side vulnerable on the break.
    ("possession", "counter_attack"): -0.10,
    ("counter_attack", "possession"): 0.20,
    # Wing play vs narrow formations: wide overloads stretch compact defences.
    ("wing_play", "defensive_block"): 0.20,
    ("wing_play", "possession"): 0.05,
    ("defensive_block", "wing_play"): -0.10,
    # Direct vs possession: direct balls bypass midfield presses.
    ("direct", "possession"): 0.10,
    ("possession", "direct"): 0.10,  # possession teams can control the tempo
    # Direct vs high press: pressing vs long balls is a gamble.
    ("direct", "high_press"): 0.05,
    ("high_press", "direct"): 0.05,
    # Counter-attack vs high press: the classic trap game.
    ("counter_attack", "high_press"): 0.15,
    ("high_press", "counter_attack"): -0.10,
    # Possession vs possession: cancelled out.
    ("possession", "possession"): 0.05,
    # General mirrors.
    ("counter_attack", "counter_attack"): 0.0,
    ("high_press", "high_press"): 0.0,
    ("defensive_block", "defensive_block"): 0.0,
    ("direct", "direct"): 0.0,
    ("wing_play", "wing_play"): 0.0,
}

# Formation compatibility bonuses.
_FORMATION_EDGE: dict[tuple[str, str], float] = {
    # 4-3-3 vs 3-5-2: wide forwards exploit wing-back spaces.
    ("4-3-3", "3-5-2"): 0.08,
    ("4-3-3", "5-3-2"): 0.05,
    # 4-2-3-1 vs 4-4-2: the extra midfielder between lines.
    ("4-2-3-1", "4-4-2"): 0.08,
    # 3-5-2 vs 4-3-3: extra centre-back nullifies wide threat.
    ("3-5-2", "4-3-3"): 0.05,
    ("3-5-2", "4-2-3-1"): 0.05,
    # 5-3-2 neutralises wing play.
    ("5-3-2", "4-3-3"): 0.05,
    # 4-4-2 vs 4-3-3: midfield overload.
    ("4-3-3", "4-4-2"): 0.05,
}


# ── All 48 World Cup 2026 Teams ─────────────────────────────────────────────


_TEAM_PROFILES: dict[str, TacticalProfile] = {}


def _register(
    team: str,
    playing_style: str,
    formation_preference: str,
    strengths: list[str],
    weaknesses: list[str],
    key_player: str,
    coach_style_summary: str,
    fifa_rank: int = 50,
) -> None:
    _TEAM_PROFILES[team.casefold()] = TacticalProfile(
        team=team,
        playing_style=playing_style,
        formation_preference=formation_preference,
        strengths=strengths,
        weaknesses=weaknesses,
        key_player=key_player,
        coach_style_summary=coach_style_summary,
        fifa_rank=fifa_rank,
    )


# ── UEFA (Europe) — 16 teams ────────────────────────────────────────────────

_register(
    "France",
    playing_style="possession",
    formation_preference="4-3-3",
    strengths=["pace on the counter", "midfield creativity", "defensive depth", "set-piece threat"],
    weaknesses=["occasional complacency", "centre-back partnership turnover", "Mbappe-dependence"],
    key_player="Kylian Mbappe",
    coach_style_summary="Didier Deschamps — pragmatic winner, blends possession control with devastating counter-attacks",
    fifa_rank=2,
)

_register(
    "England",
    playing_style="possession",
    formation_preference="4-2-3-1",
    strengths=["attacking depth", "set-piece conversion", "youth integration", "full-back quality"],
    weaknesses=["defensive transitions", "midfield balance against elite press", "penalty shootout record"],
    key_player="Jude Bellingham",
    coach_style_summary="Thomas Tuchel — high-intensity positional play with tactical flexibility",
    fifa_rank=4,
)

_register(
    "Spain",
    playing_style="possession",
    formation_preference="4-3-3",
    strengths=["technical control", "youth pipeline (La Masia)", "pressing structure", "possession recycling"],
    weaknesses=["lack of classic No. 9", "physical vulnerability in duels", "over-possession without penetration"],
    key_player="Lamine Yamal",
    coach_style_summary="Luis de la Fuente — fluid attacking patterns, wide overloads, high technical floor",
    fifa_rank=3,
)

_register(
    "Germany",
    playing_style="possession",
    formation_preference="4-2-3-1",
    strengths=["midfield engine", "pressing intensity", "tournament experience", "versatile attackers"],
    weaknesses=["full-back depth", "traditional No. 9 question", "defensive high-line vulnerability"],
    key_player="Jamal Musiala",
    coach_style_summary="Julian Nagelsmann — aggressive pressing, position-fluid attack, high defensive line",
    fifa_rank=10,
)

_register(
    "Portugal",
    playing_style="possession",
    formation_preference="4-3-3",
    strengths=["generational talent pool", "defensive organisation", "midfield craft", "wide creativity"],
    weaknesses=["Ronaldo age management", "centre-forward depth", "big-game mentality"],
    key_player="Bruno Fernandes",
    coach_style_summary="Roberto Martinez — flexible system builder, wing-heavy creation, veteran trust",
    fifa_rank=6,
)

_register(
    "Netherlands",
    playing_style="possession",
    formation_preference="4-3-3",
    strengths=["defensive solidity (Van Dijk)", "wing-back quality", "midfield progression", "aerial dominance"],
    weaknesses=["striker depth behind Gakpo/Depay", "wide-defender pace", "tournament knockout fragility"],
    key_player="Virgil van Dijk",
    coach_style_summary="Ronald Koeman — Dutch school build-up, dual-pivot control, set-piece emphasis",
    fifa_rank=7,
)

_register(
    "Italy",
    playing_style="possession",
    formation_preference="3-5-2",
    strengths=["defensive organisation", "midfield tenacity (Barella)", "tactical intelligence", "counter-attack efficiency"],
    weaknesses=["striker consistency", "wide-creative depth", "generational transition"],
    key_player="Nicolo Barella",
    coach_style_summary="Luciano Spalletti — positional rotations, high press, wing-back width",
    fifa_rank=9,
)

_register(
    "Belgium",
    playing_style="possession",
    formation_preference="4-2-3-1",
    strengths=["midfield creativity (De Bruyne)", "individual brilliance", "experience"],
    weaknesses=["ageing golden generation", "defensive pace", "goalkeeper transition"],
    key_player="Kevin De Bruyne",
    coach_style_summary="Rudi Garcia — pragmatic organisation, maximising remaining elite talent",
    fifa_rank=8,
)

_register(
    "Croatia",
    playing_style="possession",
    formation_preference="4-3-3",
    strengths=["midfield mastery (Modric)", "tournament mentality", "passing control", "compact shape"],
    weaknesses=["ageing core", "striker output", "athleticism in transitions"],
    key_player="Luka Modric",
    coach_style_summary="Zlatko Dalic — disciplined possession, midfield triangle, tournament resilience",
    fifa_rank=12,
)

_register(
    "Switzerland",
    playing_style="defensive_block",
    formation_preference="4-2-3-1",
    strengths=["defensive structure", "counter-attack discipline", "big-game upsets", "team cohesion"],
    weaknesses=["creative ceiling", "striker depth", "pace in wide areas"],
    key_player="Granit Xhaka",
    coach_style_summary="Murat Yakin — compact mid-block, fast vertical transitions, set-piece specialisation",
    fifa_rank=19,
)

_register(
    "Denmark",
    playing_style="high_press",
    formation_preference="4-3-3",
    strengths=["collective pressing", "midfield running power (Hojbjerg)", "set-piece threat", "team unity"],
    weaknesses=["star-power ceiling", "depth behind starters", "goal-scoring consistency"],
    key_player="Rasmus Hojlund",
    coach_style_summary="Brian Riemer — high-energy pressing, direct wing play, physical duels emphasis",
    fifa_rank=21,
)

_register(
    "Austria",
    playing_style="high_press",
    formation_preference="4-2-3-1",
    strengths=["intense pressing (Rangnick-ball)", "midfield work-rate", "counter-pressing transitions"],
    weaknesses=["defensive depth", "individual quality gap vs elite", "in-game adaptation"],
    key_player="David Alaba",
    coach_style_summary="Ralf Rangnick — gegenpressing originator, vertical chaos, intense duels",
    fifa_rank=22,
)

_register(
    "Ukraine",
    playing_style="counter_attack",
    formation_preference="4-3-3",
    strengths=["pace in transitions", "wide-forward quality (Mudryk)", "defensive resilience", "team spirit"],
    weaknesses=["squad depth", "midfield physicality", "set-piece defending"],
    key_player="Mykhailo Mudryk",
    coach_style_summary="Serhiy Rebrov — compact shape, speed on the break, emotional resilience",
    fifa_rank=25,
)

_register(
    "Serbia",
    playing_style="direct",
    formation_preference="3-5-2",
    strengths=["physical presence", "aerial dominance", "striker quality (Vlahovic/Mitrovic)", "set-piece power"],
    weaknesses=["defensive mobility", "wide-defender pace", "midfield creativity"],
    key_player="Dusan Vlahovic",
    coach_style_summary="Dragan Stojkovic — direct, physical, wide crosses, two-striker system",
    fifa_rank=32,
)

_register(
    "Poland",
    playing_style="direct",
    formation_preference="4-4-2",
    strengths=["striker class (Lewandowski)", "set-piece threat", "physical defending", "goalkeeper quality (Szczesny)"],
    weaknesses=["midfield creativity", "pace in transition defence", "ball progression"],
    key_player="Robert Lewandowski",
    coach_style_summary="Michal Probierz — direct balls to target man, compact block, counter-threat",
    fifa_rank=28,
)

_register(
    "Turkey",
    playing_style="counter_attack",
    formation_preference="4-2-3-1",
    strengths=["young attacking talent (Guler)", "pace on the break", "midfield energy", "home-crowd diaspora"],
    weaknesses=["defensive organisation", "in-game discipline (cards)", "consistency"],
    key_player="Arda Guler",
    coach_style_summary="Vincenzo Montella — fast transitions, youthful aggression, attacking freedom",
    fifa_rank=26,
)


# ── CONMEBOL (South America) — 7 teams ──────────────────────────────────────

_register(
    "Argentina",
    playing_style="possession",
    formation_preference="4-3-3",
    strengths=["Messi orchestrator", "midfield cohesion", "defensive organisation", "tournament know-how"],
    weaknesses=["Messi age/dependency", "full-back pace", "physical intensity vs European elite"],
    key_player="Lionel Messi",
    coach_style_summary="Lionel Scaloni — balanced possession, tactical adaptability, protecting Messi's freedom",
    fifa_rank=1,
)

_register(
    "Brazil",
    playing_style="possession",
    formation_preference="4-2-3-1",
    strengths=["attacking flair (Vinicius Jr)", "full-back quality", "squad depth", "individual brilliance"],
    weaknesses=["midfield defensive balance", "coaching instability", "tournament pressure"],
    key_player="Vinicius Jr",
    coach_style_summary="Dorival Junior — wing-focused creation, full-back overlaps, flair-first approach",
    fifa_rank=5,
)

_register(
    "Uruguay",
    playing_style="high_press",
    formation_preference="4-2-3-1",
    strengths=["intense pressing (Bielsa)", "midfield engine (Valverde)", "defensive grit", "set-piece threat"],
    weaknesses=["squad depth vs giants", "over-aggression (cards)", "striker conversion consistency"],
    key_player="Federico Valverde",
    coach_style_summary="Marcelo Bielsa — man-marking press, vertical intensity, high-risk high-reward",
    fifa_rank=11,
)

_register(
    "Colombia",
    playing_style="possession",
    formation_preference="4-2-3-1",
    strengths=["midfield creativity (James)", "wide threat (Diaz)", "unbeaten run mentality", "fan energy"],
    weaknesses=["defensive concentration", "tournament knockout record", "keeper depth"],
    key_player="Luis Diaz",
    coach_style_summary="Nestor Lorenzo — possession-based build-up, James free role, high line",
    fifa_rank=13,
)

_register(
    "Ecuador",
    playing_style="high_press",
    formation_preference="4-3-3",
    strengths=["midfield dynamism (Caicedo)", "defensive solidity", "youth pipeline", "altitude-adapted fitness"],
    weaknesses=["goal-scoring output", "creative depth", "in-game management"],
    key_player="Moises Caicedo",
    coach_style_summary="Sebastian Beccacece — intense pressing, quick transitions, youthful energy",
    fifa_rank=24,
)

_register(
    "Paraguay",
    playing_style="defensive_block",
    formation_preference="4-4-2",
    strengths=["defensive organisation", "counter-attack threat (Almiron)", "physical duels", "set-piece routine"],
    weaknesses=["ball possession", "creative ceiling", "depth beyond starters"],
    key_player="Miguel Almiron",
    coach_style_summary="Gustavo Alfaro — deep block, fast counters, physical war of attrition",
    fifa_rank=45,
)

_register(
    "Chile",
    playing_style="high_press",
    formation_preference="4-3-3",
    strengths=["pressing intensity", "veteran leadership (Sanchez/Vidal)", "midfield work-rate"],
    weaknesses=["ageing core", "goal-scoring drop-off", "defensive pace"],
    key_player="Alexis Sanchez",
    coach_style_summary="Ricardo Gareca — aggressive press, wide-attack emphasis, veteran loyalty",
    fifa_rank=40,
)


# ── CONCACAF (North America) — 6 teams ──────────────────────────────────────

_register(
    "USA",
    playing_style="high_press",
    formation_preference="4-3-3",
    strengths=["midfield engine (McKennie/Adams)", "wing pace (Pulisic)", "athletic depth", "home advantage"],
    weaknesses=["centre-back partnership", "striker consistency", "tournament experience"],
    key_player="Christian Pulisic",
    coach_style_summary="Mauricio Pochettino — high press, positional play, European-calibre tactical preparation",
    fifa_rank=16,
)

_register(
    "Mexico",
    playing_style="possession",
    formation_preference="4-3-3",
    strengths=["possession control", "home altitude advantage", "wide threat (Lozano)", "tournament consistency"],
    weaknesses=["striker output", "defensive pace vs elite attackers", "quarterfinal ceiling"],
    key_player="Hirving Lozano",
    coach_style_summary="Javier Aguirre — possession-dominant, wide overloads, emotional leadership",
    fifa_rank=17,
)

_register(
    "Canada",
    playing_style="counter_attack",
    formation_preference="4-4-2",
    strengths=["speed on the break (Davies/David)", "athleticism", "set-piece height", "home conditions"],
    weaknesses=["defensive organisation", "midfield depth", "tournament experience at this level"],
    key_player="Alphonso Davies",
    coach_style_summary="Jesse Marsch — direct transitions, pressing triggers, vertical aggression",
    fifa_rank=30,
)

_register(
    "Costa Rica",
    playing_style="defensive_block",
    formation_preference="5-3-2",
    strengths=["defensive resilience", "goalkeeper heroics (Navas)", "counter-attack patience", "tournament know-how"],
    weaknesses=["goal-scoring", "possession stats", "ageing core"],
    key_player="Keylor Navas",
    coach_style_summary="Claudio Vivas — deep 5-3-2 block, soak-and-strike, experience-first selections",
    fifa_rank=42,
)

_register(
    "Panama",
    playing_style="defensive_block",
    formation_preference="4-4-2",
    strengths=["physical duels", "set-piece threat", "team cohesion", "counter-attack speed"],
    weaknesses=["technical ceiling", "possession quality", "bench depth"],
    key_player="Michael Murillo",
    coach_style_summary="Thomas Christiansen — compact 4-4-2, direct balls, set-piece focus",
    fifa_rank=55,
)

_register(
    "Jamaica",
    playing_style="counter_attack",
    formation_preference="4-2-3-1",
    strengths=["pace in attack (Bailey)", "Premier League diaspora", "athleticism", "set-piece height"],
    weaknesses=["defensive organisation", "goalkeeper consistency", "midfield ball retention"],
    key_player="Leon Bailey",
    coach_style_summary="Steve McClaren — fast transitions, wide counters, Premier League physical blueprint",
    fifa_rank=58,
)


# ── AFC (Asia) — 8 teams ────────────────────────────────────────────────────

_register(
    "Japan",
    playing_style="possession",
    formation_preference="4-2-3-1",
    strengths=["technical quality", "midfield coordination", "defensive discipline", "tactical preparation"],
    weaknesses=["physicality vs top European sides", "centre-forward finishing", "height disadvantage"],
    key_player="Kaoru Mitoma",
    coach_style_summary="Hajime Moriyasu — patient possession, positional rotations, meticulous game plans",
    fifa_rank=15,
)

_register(
    "Iran",
    playing_style="defensive_block",
    formation_preference="4-4-2",
    strengths=["defensive organisation", "counter-attack efficiency (Taremi)", "physicality", "set-piece threat"],
    weaknesses=["possession vs elite teams", "creative depth", "disciplinary record"],
    key_player="Mehdi Taremi",
    coach_style_summary="Amir Ghalenoei — low-block resilience, direct to front two, physical style",
    fifa_rank=18,
)

_register(
    "South Korea",
    playing_style="counter_attack",
    formation_preference="4-3-3",
    strengths=["pace on the break (Son)", "midfield work-rate", "fitness levels", "set-piece danger"],
    weaknesses=["defensive concentration", "depth beyond stars", "physicality in duels"],
    key_player="Son Heung-min",
    coach_style_summary="Hong Myung-bo — fast counters, Son-focused attack, disciplined shape out of possession",
    fifa_rank=23,
)

_register(
    "Saudi Arabia",
    playing_style="possession",
    formation_preference="4-3-3",
    strengths=["domestic league investment", "possession comfort", "fitness", "home-region conditions"],
    weaknesses=["international tournament experience", "defensive pace", "finishing consistency"],
    key_player="Salem Al-Dawsari",
    coach_style_summary="Roberto Mancini — possession football, European tactical framework, disciplined shape",
    fifa_rank=35,
)

_register(
    "Australia",
    playing_style="direct",
    formation_preference="4-4-2",
    strengths=["physical presence", "aerial dominance", "set-piece threat", "fighting spirit"],
    weaknesses=["technical ceiling", "possession vs top teams", "pace in wide defence"],
    key_player="Mathew Ryan",
    coach_style_summary="Tony Popovic — direct, physical, aerial threat, compact defensive shape",
    fifa_rank=33,
)

_register(
    "Uzbekistan",
    playing_style="possession",
    formation_preference="4-2-3-1",
    strengths=["technical midfield", "youth development pipeline", "disciplined shape"],
    weaknesses=["tournament experience", "goal-scoring vs elite", "physical intensity"],
    key_player="Eldor Shomurodov",
    coach_style_summary="Srecko Katanec — organised build-up, patient approach, youth integration",
    fifa_rank=48,
)

_register(
    "UAE",
    playing_style="counter_attack",
    formation_preference="4-4-2",
    strengths=["pace in transitions", "naturalised talent", "goalkeeping quality"],
    weaknesses=["possession under pressure", "midfield creativity", "tournament depth"],
    key_player="Ali Mabkhout",
    coach_style_summary="Paulo Bento — compact mid-block, quick counters, disciplined defensive shape",
    fifa_rank=62,
)

_register(
    "Qatar",
    playing_style="possession",
    formation_preference="4-3-3",
    strengths=["technical base (Aspire Academy)", "familiar conditions", "possession comfort"],
    weaknesses=["international calibre vs top 20", "physical intensity", "defensive concentration"],
    key_player="Akram Afif",
    coach_style_summary="Tintin Marquez — possession-oriented, Aspire Academy blueprint, attacking fluidity",
    fifa_rank=37,
)


# ── CAF (Africa) — 9 teams ──────────────────────────────────────────────────

_register(
    "Morocco",
    playing_style="counter_attack",
    formation_preference="4-3-3",
    strengths=["defensive organisation", "wide pace (Hakimi)", "midfield steel (Amrabat)", "2022 momentum"],
    weaknesses=["striker depth", "possession dominance", "creative consistency"],
    key_player="Achraf Hakimi",
    coach_style_summary="Walid Regragui — compact block, devastating transitions, emotional team leadership",
    fifa_rank=14,
)

_register(
    "Senegal",
    playing_style="high_press",
    formation_preference="4-3-3",
    strengths=["athleticism", "wing pace (Mane/Sarr)", "midfield power", "defensive organisation"],
    weaknesses=["goalkeeper consistency (post-Mendy)", "central creativity", "in-game patience"],
    key_player="Sadio Mane",
    coach_style_summary="Pape Thiaw — intense pressing, physical dominance, fast wing transitions",
    fifa_rank=20,
)

_register(
    "Nigeria",
    playing_style="wing_play",
    formation_preference="4-3-3",
    strengths=["forward depth (Osimhen/Lookman)", "wide pace", "physicality", "goals from anywhere"],
    weaknesses=["defensive organisation", "goalkeeper quality", "midfield cohesion"],
    key_player="Victor Osimhen",
    coach_style_summary="Eric Chelle — attacking freedom, wing emphasis, forward-firepower maximisation",
    fifa_rank=36,
)

_register(
    "Egypt",
    playing_style="possession",
    formation_preference="4-3-3",
    strengths=["Salah individual brilliance", "midfield control", "defensive discipline", "tournament experience"],
    weaknesses=["Salah-dependency", "striker depth", "pace in defensive transitions"],
    key_player="Mohamed Salah",
    coach_style_summary="Hossam Hassan — Salah-centric attack, possession base, experienced approach",
    fifa_rank=31,
)

_register(
    "Ivory Coast",
    playing_style="wing_play",
    formation_preference="4-3-3",
    strengths=["wing talent (Adingra/Diakite)", "athletic midfield", "squad depth", "2023 AFCON mentality"],
    weaknesses=["defensive concentration", "big-game composure", "goalkeeper experience"],
    key_player="Simon Adingra",
    coach_style_summary="Emerse Fae — wing-heavy attack, athletic transitions, resilient mentality",
    fifa_rank=34,
)

_register(
    "Algeria",
    playing_style="possession",
    formation_preference="4-2-3-1",
    strengths=["technical quality (Mahrez)", "possession comfort", "attacking creativity"],
    weaknesses=["defensive transitions", "tournament pressure (2022/2024 exits)", "physical edge"],
    key_player="Riyad Mahrez",
    coach_style_summary="Vladimir Petkovic — possession football, creative freedom, tactical flexibility",
    fifa_rank=38,
)

_register(
    "Tunisia",
    playing_style="defensive_block",
    formation_preference="4-3-3",
    strengths=["defensive structure", "midfield work-rate", "tournament discipline", "organisation"],
    weaknesses=["goal-scoring output", "individual quality", "possession vs top sides"],
    key_player="Ellyes Skhiri",
    coach_style_summary="Faouzi Benzarti — organised low-block, counter-punching, disciplined team shape",
    fifa_rank=41,
)

_register(
    "Cameroon",
    playing_style="direct",
    formation_preference="4-3-3",
    strengths=["physical power", "pace on the break", "set-piece threat", "tournament pedigree"],
    weaknesses=["tactical discipline", "midfield creativity", "goalkeeping consistency"],
    key_player="Vincent Aboubakar",
    coach_style_summary="Marc Brys — direct, physical, pace-dependent, attacking freedom",
    fifa_rank=43,
)

_register(
    "Ghana",
    playing_style="counter_attack",
    formation_preference="4-2-3-1",
    strengths=["midfield power (Partey)", "wide pace (Kudus)", "athleticism", "tournament experience"],
    weaknesses=["defensive organisation", "goalkeeper stability", "in-game discipline"],
    key_player="Mohammed Kudus",
    coach_style_summary="Otto Addo — fast counters, midfield physicality, Kudus free-role creativity",
    fifa_rank=47,
)


# ── OFC (Oceania) — 1 team ──────────────────────────────────────────────────

_register(
    "New Zealand",
    playing_style="direct",
    formation_preference="4-4-2",
    strengths=["physical presence", "set-piece threat (Wood)", "team cohesion", "underdog mentality"],
    weaknesses=["technical level vs top 50", "pace outside Wood", "possession capability"],
    key_player="Chris Wood",
    coach_style_summary="Darren Bazeley — direct to target man, physical duels, compact defensive shape",
    fifa_rank=80,
)


# ── Inter-confederation Playoff Teams (2 slots) ────────────────────────────

_register(
    "Peru",
    playing_style="defensive_block",
    formation_preference="4-2-3-1",
    strengths=["defensive organisation", "midfield experience", "set-piece routines", "tournament scrappiness"],
    weaknesses=["goal-scoring", "pace in attack", "creative depth"],
    key_player="Gianluca Lapadula",
    coach_style_summary="Oscar Ibanez — deep block, defensive platform, opportunistic transitions",
    fifa_rank=39,
)

_register(
    "Honduras",
    playing_style="direct",
    formation_preference="4-4-2",
    strengths=["physical duels", "aerial threat", "counter-attack directness", "CONCACAF grit"],
    weaknesses=["possession quality", "technical ceiling", "defensive pace"],
    key_player="Alberth Elis",
    coach_style_summary="Reinaldo Rueda — direct, physical, aerial approach, compact defensive block",
    fifa_rank=68,
)

# ── Additional teams to reach 48 total ──────────────────────────────────────

_register(
    "Sweden",
    playing_style="direct",
    formation_preference="4-4-2",
    strengths=["physical presence", "set-piece threat", "defensive structure", "collective work-rate"],
    weaknesses=["creative flair vs elite", "pace on the wings", "depth behind Isak/Gyokeres"],
    key_player="Alexander Isak",
    coach_style_summary="Jon Dahl Tomasson — direct 4-4-2, target-man combination play, physical duels",
    fifa_rank=27,
)

_register(
    "Norway",
    playing_style="possession",
    formation_preference="4-3-3",
    strengths=["Haaland goalscoring", "midfield creativity (Odegaard)", "youth talent", "physical profile"],
    weaknesses=["tournament inexperience", "defensive depth", "goalkeeper consistency"],
    key_player="Erling Haaland",
    coach_style_summary="Stale Solbakken — Haaland-focused attack, possession build-up, Odegaard orchestrator",
    fifa_rank=44,
)

_register(
    "Hungary",
    playing_style="high_press",
    formation_preference="3-4-2-1",
    strengths=["collective pressing", "counter-attack speed", "midfield engine (Szoboszlai)", "set-piece delivery"],
    weaknesses=["defensive depth", "individual quality vs elite", "tournament record"],
    key_player="Dominik Szoboszlai",
    coach_style_summary="Marco Rossi — aggressive 3-4-2-1 press, fast transitions, Szoboszlai free role",
    fifa_rank=29,
)

_register(
    "Greece",
    playing_style="defensive_block",
    formation_preference="4-3-3",
    strengths=["defensive organisation", "set-piece threat", "tournament upset capability", "goalkeeper quality"],
    weaknesses=["goal-scoring output", "possession vs top teams", "creative depth"],
    key_player="Konstantinos Mavropanos",
    coach_style_summary="Ivan Jovanovic — compact block, physical defence, counter-punching strategy",
    fifa_rank=46,
)

_register(
    "Scotland",
    playing_style="direct",
    formation_preference="3-4-2-1",
    strengths=["physical intensity", "set-piece threat", "midfield running power", "home-crowd diaspora"],
    weaknesses=["technical ceiling", "striker depth", "defensive pace"],
    key_player="Scott McTominay",
    coach_style_summary="Steve Clarke — direct 3-4-2-1, physical overload, midfield runners",
    fifa_rank=49,
)

_register(
    "Wales",
    playing_style="defensive_block",
    formation_preference="3-4-2-1",
    strengths=["defensive organisation", "wide transitions", "set-piece delivery", "tournament experience"],
    weaknesses=["goal-scoring post-Bale", "creative midfield", "depth"],
    key_player="Brennan Johnson",
    coach_style_summary="Craig Bellamy — compact 3-4-2-1, fast wing-backs, disciplined defence",
    fifa_rank=50,
)

_register(
    "Czech Republic",
    playing_style="high_press",
    formation_preference="4-2-3-1",
    strengths=["midfield pressing (Soucek)", "set-piece threat", "physical duels", "tournament pedigree"],
    weaknesses=["attacking creativity", "pace at full-back", "depth"],
    key_player="Tomas Soucek",
    coach_style_summary="Ivan Hasek — high-intensity pressing, aerial dominance, organised transitions",
    fifa_rank=51,
)

_register(
    "Venezuela",
    playing_style="counter_attack",
    formation_preference="4-4-2",
    strengths=["pace on the break", "defensive grit", "youth development", "growing confidence"],
    weaknesses=["tournament experience", "possession quality", "depth"],
    key_player="Yeferson Soteldo",
    coach_style_summary="Fernando Batista — compact block, speed on counters, youthful energy",
    fifa_rank=52,
)

_register(
    "Bolivia",
    playing_style="defensive_block",
    formation_preference="4-4-2",
    strengths=["altitude advantage (if home)", "physical duels", "team familiarity"],
    weaknesses=["away-form vulnerability", "technical ceiling", "pace"],
    key_player="Marcelo Martins Moreno",
    coach_style_summary="Antonio Carlos Zago — deep block, altitude-tuned fitness, direct transitions",
    fifa_rank=74,
)

_register(
    "South Africa",
    playing_style="counter_attack",
    formation_preference="4-2-3-1",
    strengths=["pace on the break", "midfield mobility", "AFCON competitive level", "youth development"],
    weaknesses=["goal-scoring consistency", "tournament experience at this level", "defensive concentration"],
    key_player="Percy Tau",
    coach_style_summary="Hugo Broos — fast counters, compact mid-block, AFCON experience blueprint",
    fifa_rank=53,
)


# ── Public API ──────────────────────────────────────────────────────────────


def get_team_profile(team_name: str) -> TacticalProfile | None:
    """Return the tactical profile for a given team, or None if not found."""
    return _TEAM_PROFILES.get(team_name.casefold())


def list_all_teams() -> list[str]:
    """Return all registered team names (sorted)."""
    return sorted(p.team for p in _TEAM_PROFILES.values() if p is not None)


def analyze_tactical_matchup(
    home_team: str,
    away_team: str,
) -> dict[str, Any]:
    """Compare tactical profiles and compute a tactical_advantage score.

    Returns a dict with:
    - tactical_advantage: float ∈ [-1.0, +1.0], positive favours home
    - style_matchup: description of style contrast
    - formation_analysis: formation matchup summary
    - mismatches: list of identified tactical mismatches
    - home_profile / away_profile: team tactical profiles (or None)
    """
    home = get_team_profile(home_team)
    away = get_team_profile(away_team)

    if home is None or away is None:
        missing = []
        if home is None:
            missing.append(home_team)
        if away is None:
            missing.append(away_team)
        return {
            "tactical_advantage": 0.0,
            "style_matchup": "Unknown — one or both teams not in tactical database",
            "formation_analysis": "N/A",
            "mismatches": [],
            "home_profile": home,
            "away_profile": away,
            "missing_teams": missing,
        }

    # Base style advantage
    style_pair = (home.playing_style, away.playing_style)
    base_advantage = _STYLE_MATCHUP.get(style_pair, 0.0)

    # Formation edge
    formation_pair = (home.formation_preference, away.formation_preference)
    formation_bonus = _FORMATION_EDGE.get(formation_pair, 0.0)

    # FIFA rank modifier: significant rank gap shifts advantage
    rank_gap = home.fifa_rank - away.fifa_rank
    # Normalise: rank gap of 30 ≈ 0.15 advantage shift (lower rank = better team)
    rank_modifier = max(-0.20, min(0.20, -rank_gap * 0.005))

    # Style compatibility descriptions
    style_descriptions = _style_describe(home, away)

    # Compute final tactical advantage
    tactical_advantage = base_advantage + formation_bonus + rank_modifier
    tactical_advantage = max(-1.0, min(1.0, tactical_advantage))

    # Identify mismatches
    mismatches = _identify_mismatches(home, away)

    return {
        "tactical_advantage": round(tactical_advantage, 4),
        "style_matchup": style_descriptions,
        "formation_analysis": (
            f"{home.formation_preference} (home) vs {away.formation_preference} (away): "
            f"{_formation_comment(home.formation_preference, away.formation_preference)}"
        ),
        "mismatches": mismatches,
        "home_profile": home,
        "away_profile": away,
        "breakdown": {
            "style_base": round(base_advantage, 4),
            "formation_bonus": round(formation_bonus, 4),
            "rank_modifier": round(rank_modifier, 4),
        },
    }


def generate_tactical_analysis(home_team: str, away_team: str) -> str:
    """Generate a 2-3 paragraph tactical breakdown for a given matchup.

    Returns a natural-language string suitable for display or inclusion
    in a deep analysis prompt.
    """
    home = get_team_profile(home_team)
    away = get_team_profile(away_team)

    if home is None or away is None:
        missing = []
        if home is None:
            missing.append(home_team)
        if away is None:
            missing.append(away_team)
        return (
            f"战术分析不可用：以下球队未收录于战术数据库中：{'、'.join(missing)}"
        )

    matchup = analyze_tactical_matchup(home_team, away_team)
    advantage = matchup["tactical_advantage"]

    # Determine advantage direction
    h_style = _style_name(home.playing_style)
    a_style = _style_name(away.playing_style)
    if advantage > 0.10:
        advantage_line = (
            f"从战术匹配度来看，{home.team} 占优（优势评分 {advantage:+.2f}）。"
            f"{home.team} 的 {h_style} 风格对 {away.team} 的 "
            f"{a_style} 体系形成了有效的克制。"
        )
    elif advantage < -0.10:
        advantage_line = (
            f"从战术匹配度来看，{away.team} 在客场反而占据优势（评分 {advantage:+.2f}）。"
            f"{away.team} 的 {a_style} 打法很可能克制 {home.team} 的 "
            f"{h_style} 体系。"
        )
    else:
        advantage_line = (
            f"战术层面双方势均力敌（评分 {advantage:+.2f}），"
            f"{home.team} 的 {h_style} 与 {away.team} 的 "
            f"{a_style} 体系相互制衡。"
        )

    # Strengths and weaknesses paragraph
    sw_paragraph = (
        f"{home.team} 的核心优势在于 {', '.join(home.strengths[:3])}，"
        f"由 {home.coach_style_summary.split(' — ')[0]} 教练打造的 {home.formation_preference} 阵型"
        f"强调 {home.coach_style_summary.split(' — ')[1] if ' — ' in home.coach_style_summary else home.coach_style_summary}。"
        f"然而{home.weaknesses[0]}是其软肋。"
        f"\n\n{away.team} 方面，{', '.join(away.strengths[:3])}是其主要武器，"
        f"{away.formation_preference} 体系支撑着 {away.coach_style_summary.split(' — ')[0] if ' — ' in away.coach_style_summary else ''}"
        f"的战术理念。但{away.weaknesses[0]}可能成为突破口。"
    )

    # Key player / mismatch paragraph
    mismatches = matchup["mismatches"]
    if mismatches:
        mismatch_lines = "\n".join(f"• {m}" for m in mismatches[:3])
        kp_paragraph = (
            f"关键对位方面，{home.key_player}（{home.team}）与 {away.key_player}"
            f"（{away.team}）的表现将决定比赛走向。战术错配包括：\n{mismatch_lines}"
        )
    else:
        kp_paragraph = (
            f"关键球员方面，{home.key_player}（{home.team}）和 {away.key_player}"
            f"（{away.team}）的对决将直接左右比赛局势。"
        )

    return f"{advantage_line}\n\n{sw_paragraph}\n\n{kp_paragraph}"


# ── Helpers ─────────────────────────────────────────────────────────────────


def _style_describe(home: TacticalProfile, away: TacticalProfile) -> str:
    """Produce a compact description of the style matchup."""
    styles = {
        "possession": "控球主导",
        "counter_attack": "防守反击",
        "high_press": "高位压迫",
        "defensive_block": "低位防守",
        "direct": "直接打法",
        "wing_play": "边路进攻",
    }
    hs = styles.get(home.playing_style, home.playing_style)
    aws = styles.get(away.playing_style, away.playing_style)

    if home.playing_style == "high_press" and away.playing_style == "defensive_block":
        return f"{home.team}的高位压迫 vs {away.team}的低位防守：矛与盾的对决，压迫方需警惕反击"
    elif home.playing_style == "possession" and away.playing_style == "counter_attack":
        return f"{home.team}的控球打法 vs {away.team}的防守反击：经典控球与反击的博弈，控球方需防转换"
    elif home.playing_style == "direct" and away.playing_style == "possession":
        return f"{home.team}的直接打法 vs {away.team}的传控体系：物理对抗与技术的碰撞"
    elif home.playing_style == "counter_attack" and away.playing_style == "high_press":
        return f"{home.team}的防守反击 vs {away.team}的高位压迫：反击空间可能很大"
    elif home.playing_style == "wing_play" and away.playing_style == "defensive_block":
        return f"{home.team}的边路强攻 vs {away.team}的低位防守：宽度利用是关键"
    else:
        return f"{home.team}的{hs} vs {away.team}的{aws}"


def _formation_comment(home_fmt: str, away_fmt: str) -> str:
    """Comment on formation matchup."""
    if home_fmt == away_fmt:
        return "阵型镜像，中场人员对位成为关键"
    if "3-5-2" in (home_fmt, away_fmt) and "4-3-3" in (home_fmt, away_fmt):
        return "3后卫体系与4后卫体系的对决，边路走廊将决定攻防节奏"
    if "4-2-3-1" in (home_fmt, away_fmt) and "4-4-2" in (home_fmt, away_fmt):
        return "双前锋对双中卫，4-2-3-1的中场人数优势可能是决定性因素"
    return "不同阵型结构，赛前部署与赛中调整将起关键作用"


def _identify_mismatches(
    home: TacticalProfile, away: TacticalProfile
) -> list[str]:
    """Identify tactical mismatches between two teams."""
    mismatches: list[str] = []

    # Style mismatches
    if home.playing_style == "high_press" and away.playing_style == "possession":
        mismatches.append(
            f"{home.team}的高位压迫可能会迫使{away.team}后场出球失误，"
            f"这是传控球队最忌惮的战术"
        )
    if home.playing_style == "possession" and away.playing_style == "counter_attack":
        mismatches.append(
            f"{away.team}的快速反击是{home.team}控球时的最大威胁，"
            f"攻守转换瞬间的防守组织将受到严峻考验"
        )
    if home.playing_style == "wing_play" and "3" in away.formation_preference[:1]:
        mismatches.append(
            f"{home.team}的边路进攻可能恰好攻击{away.team}"
            f"{away.formation_preference}体系的翼卫身后空间"
        )

    # Formation mismatches
    if home.formation_preference == "4-3-3" and "4-4-2" in away.formation_preference:
        mismatches.append(
            f"{home.team}的4-3-3中场三人组对{away.team}的4-4-2双中场"
            f"形成人数优势，中场控制可能向主队倾斜"
        )
    if home.formation_preference == "3-5-2" and away.formation_preference == "4-3-3":
        mismatches.append(
            f"{home.team}的3-5-2翼卫可能压制{away.team}4-3-3的单边后卫，"
            f"边路二对一局面值得关注"
        )

    # Pace mismatches
    for s in home.strengths:
        if "pace" in s.lower() or "speed" in s.lower():
            for w in away.weaknesses:
                if "pace" in w.lower() or "speed" in w.lower():
                    mismatches.append(
                        f"{home.team}的速度优势 vs {away.team}的防守速度短板"
                        f"——这可能是比赛的胜负手"
                    )
                    break
            break

    return mismatches


def _style_name(style: str) -> str:
    """Translate playing style to Chinese label."""
    names = {
        "possession": "控球主导",
        "counter_attack": "防守反击",
        "high_press": "高位压迫",
        "defensive_block": "低位防守",
        "direct": "直接打法",
        "wing_play": "边路进攻",
    }
    return names.get(style, style)
