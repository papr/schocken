from offline_test_helpers import (
    MockBot,
    MockClient,
    MockMember,
    MockMessage,
)

# from schocken.exceptions import SpielLaeuft
from schocken import wuerfel
import pytest


pytestmark = pytest.mark.asyncio


@pytest.fixture
def member(n=3):
    return [MockMember(f"spieler_{i+1}") for i in range(n)]


@pytest.fixture
def bot():
    client = MockClient()
    bot = MockBot(client)
    return bot


@pytest.fixture
async def hz1_bot(member):
    # spiel läuft, spieler 1 darf anfangen
    client = MockClient()
    bot = MockBot(client)
    await bot.parse_input(MockMessage(member[0], "!schocken"))
    wuerfel.werfen = lambda n: (1,)
    await bot.parse_input(MockMessage(member[0], "!einwerfen"))
    wuerfel.werfen = lambda n: (2,)
    await bot.parse_input(MockMessage(member[1], "!einwerfen"))
    await bot.parse_input(MockMessage(member[2], "!einwerfen"))
    assert bot.game.state.stecher_liste[0].name == "spieler_1"
    return bot


@pytest.fixture
async def hz2_bot(member):
    # spiel läuft, spieler 1 darf anfangen
    client = MockClient()
    bot = MockBot(client)
    await bot.parse_input(MockMessage(member[0], "!schocken"))
    wuerfel.werfen = lambda n: (1,)
    await bot.parse_input(MockMessage(member[0], "!einwerfen"))
    wuerfel.werfen = lambda n: (2,)
    await bot.parse_input(MockMessage(member[1], "!einwerfen"))
    await bot.parse_input(MockMessage(member[2], "!einwerfen"))

    # spieler 3 verliert
    wuerfel.werfen = lambda n: (1, 1, 1)
    await bot.parse_input(MockMessage(member[0], "!wuerfeln"))
    await bot.parse_input(MockMessage(member[0], "!weiter"))
    wuerfel.werfen = lambda n: (2, 2, 1)
    await bot.parse_input(MockMessage(member[1], "!wuerfeln"))
    await bot.parse_input(MockMessage(member[2], "!wuerfeln"))
    assert bot.is_in_msg("spieler_3 verliert die Halbzeit.")
    assert bot.is_in_msg("spieler_3 ist mit `!wuerfeln` dran.")
    return bot


async def test_transition_to_finale(member, hz2_bot):
    await hz2_bot.parse_input(MockMessage(member[2], "!wuerfeln"))


async def test_start_game(member, bot):
    assert not bot.game_running
    await bot.parse_input(MockMessage(member[0], "!schocken"))
    assert bot.game_running
    await bot.parse_input(MockMessage(member[0], "!einwerfen"))
    # richtiger spieler:
    assert bot.is_in_msg("spieler_1 hat eine")
    # anderer spieler will auch starten
    await bot.parse_input(MockMessage(member[1], "!schocken"))
    assert bot.is_in_msg("Es läuft bereits ein Spiel")


async def test_einwerfen(member, bot):
    await bot.parse_input(MockMessage(member[0], "!schocken"))
    await bot.parse_input(MockMessage(member[0], "!schocken"))
    wuerfel.werfen = lambda n: (1,)
    await bot.parse_input(MockMessage(member[0], "!einwerfen"))
    wuerfel.werfen = lambda n: (2,)
    await bot.parse_input(MockMessage(member[1], "!einwerfen"))
    bot.reset_msg()
    await bot.parse_input(MockMessage(member[2], "!einwerfen"))
    expected = "spieler_1 hat mit einer EMOJI:wuerfel_1 den niedgristen Wurf."
    assert bot.is_in_msg(expected)
    # assert expected in bot.msg


async def test_weiter(member, hz1_bot):
    wuerfel.werfen = lambda n: (4, 2, 1)
    await hz1_bot.parse_input(MockMessage(member[0], "!wuerfeln"))
    await hz1_bot.parse_input(MockMessage(member[0], "!weiter"))
    high_msg = "High: MENTION:spieler_1"
    assert hz1_bot.is_in_msg(high_msg)
    low_msg = "Low: MENTION:spieler_1"
    assert hz1_bot.is_in_msg(low_msg)
    next_msg = "Als nächstes ist MENTION:spieler_2 (0 EMOJI:kronkorken)"
    assert hz1_bot.is_in_msg(next_msg)


async def test_liegen_lassen(member, hz1_bot):
    wuerfel.werfen = lambda n: (2, 2, 1)
    await hz1_bot.parse_input(MockMessage(member[0], "!wuerfeln"))
    await hz1_bot.parse_input(MockMessage(member[0], "!beiseite"))
    msg = "MENTION:spieler_1 (0 EMOJI:kronkorken) legt EMOJI:wuerfel_1 beiseite"
    assert hz1_bot.is_in_msg(msg)


async def test_runde(member, hz1_bot):
    wuerfel.werfen = lambda n: (4, 2, 1)
    await hz1_bot.parse_input(MockMessage(member[0], "!wuerfeln"))
    await hz1_bot.parse_input(MockMessage(member[0], "!weiter"))

    wuerfel.werfen = lambda n: (2, 2, 1)
    await hz1_bot.parse_input(MockMessage(member[1], "!wuerfeln"))
    low_msg = "Low: MENTION:spieler_2 (0 EMOJI:kronkorken) mit: "
    low_msg += "EMOJI:wuerfel_2 EMOJI:wuerfel_2 EMOJI:wuerfel_1"
    # spieler zwei ist low
    assert hz1_bot.is_in_msg(low_msg)
    # hat nur einen Wurf
    assert hz1_bot.is_in_msg("Als nächstes ist MENTION:spieler_3")

    wuerfel.werfen = lambda n: (3, 2, 2)
    await hz1_bot.parse_input(MockMessage(member[2], "!wuerfeln"))
    # spieler 2 verliert!
    verl_msg = "MENTION:spieler_2 verliert die Runde und bekommt 7 EMOJI:kronkorken."
    assert hz1_bot.is_in_msg(verl_msg)
    # spieler 2 fängt nächste runde an
    naechste_runde_msg = "Du bist mit `!wuerfeln` an der Reihe, "
    naechste_runde_msg += "MENTION:spieler_2 (7 EMOJI:kronkorken)."
    assert hz1_bot.is_in_msg(naechste_runde_msg)
    # 8 deckel noch in der mitte:
    assert hz1_bot.is_in_msg("Mitte: 8 EMOJI:kronkorken.")


async def test_verteilen_vorbei(member, hz1_bot):
    wuerfel.werfen = lambda n: (4, 2, 1)
    await hz1_bot.parse_input(MockMessage(member[0], "!wuerfeln"))
    await hz1_bot.parse_input(MockMessage(member[0], "!weiter"))
    await hz1_bot.parse_input(MockMessage(member[1], "!wuerfeln"))

    # spieler 3 bekommt 7
    wuerfel.werfen = lambda n: (2, 2, 1)
    await hz1_bot.parse_input(MockMessage(member[2], "!wuerfeln"))
    wuerfel.werfen = lambda n: (4, 2, 1)
    await hz1_bot.parse_input(MockMessage(member[2], "!wuerfeln"))
    await hz1_bot.parse_input(MockMessage(member[2], "!weiter"))
    await hz1_bot.parse_input(MockMessage(member[0], "!wuerfeln"))

    # spieler 2 bekommt 7
    wuerfel.werfen = lambda n: (2, 2, 1)
    await hz1_bot.parse_input(MockMessage(member[1], "!wuerfeln"))

    # spieler 2 bekommt den letzten in der mitte
    await hz1_bot.parse_input(MockMessage(member[1], "!wuerfeln"))
    await hz1_bot.parse_input(MockMessage(member[1], "!weiter"))
    wuerfel.werfen = lambda n: (3, 3, 1)
    await hz1_bot.parse_input(MockMessage(member[2], "!wuerfeln"))

    await hz1_bot.parse_input(MockMessage(member[0], "!wuerfeln"))
    s1_wirft_msg = "MENTION:spieler_1 (0 EMOJI:kronkorken) wirft EMOJI:wuerfel_3 "
    s1_wirft_msg += "EMOJI:wuerfel_3 EMOJI:wuerfel_1."
    assert hz1_bot.is_in_msg(s1_wirft_msg)
    s2_verliert_msg = "MENTION:spieler_2 verliert die Runde"
    assert hz1_bot.is_in_msg(s2_verliert_msg)
    noch_drin_msg = "Noch im Spiel: **MENTION:spieler_2 (8 EMOJI:kronkorken), "
    noch_drin_msg += "MENTION:spieler_3 (7 EMOJI:kronkorken)"
    assert hz1_bot.is_in_msg(noch_drin_msg)


async def test_halbzeit_vorbei(member, hz1_bot):
    wuerfel.werfen = lambda n: (4, 2, 1)
    await hz1_bot.parse_input(MockMessage(member[0], "!wuerfeln"))
    await hz1_bot.parse_input(MockMessage(member[0], "!weiter"))
    await hz1_bot.parse_input(MockMessage(member[1], "!wuerfeln"))
    wuerfel.werfen = lambda n: (2, 2, 1)
    await hz1_bot.parse_input(MockMessage(member[2], "!wuerfeln"))
    await hz1_bot.parse_input(MockMessage(member[2], "!wuerfeln"))
    await hz1_bot.parse_input(MockMessage(member[2], "!weiter"))
    wuerfel.werfen = lambda n: (4, 2, 1)
    await hz1_bot.parse_input(MockMessage(member[0], "!wuerfeln"))
    await hz1_bot.parse_input(MockMessage(member[1], "!wuerfeln"))
    wuerfel.werfen = lambda n: (2, 2, 1)
    await hz1_bot.parse_input(MockMessage(member[2], "!wuerfeln"))
    await hz1_bot.parse_input(MockMessage(member[2], "!weiter"))
    wuerfel.werfen = lambda n: (4, 2, 1)
    await hz1_bot.parse_input(MockMessage(member[0], "!wuerfeln"))
    await hz1_bot.parse_input(MockMessage(member[1], "!wuerfeln"))

    verl_msg = "MENTION:spieler_3 verliert die Halbzeit."
    assert hz1_bot.is_in_msg(verl_msg)
    h2_msg = "Halbzeit 2 beginnt."
    assert hz1_bot.is_in_msg(h2_msg)
    s2_dran_msg = "MENTION:spieler_3 ist mit `!wuerfeln` dran."
    assert hz1_bot.is_in_msg(s2_dran_msg)
