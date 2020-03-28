import pysm

from . import events, wuerfel
from .deckel_management import RundenDeckelManagement, SpielzeitStatus
from .exceptions import DuHastMistGebaut, FalscheAktion, FalscherSpieler, ZuOftGeworfen
from .spieler import Spieler


class Einwerfen(pysm.StateMachine):
    def __init__(self):
        super().__init__("Einwerfen")
        self.init_sm()
        self.__spieler_liste = []
        self.__stecher_count = 0
        self.__stecher_liste = []
        self.__gestochen_liste = []

    @property
    def stecher_liste(self):
        return self.__stecher_liste

    def init_sm(self):
        idle = pysm.State("einwerfen")
        stechen = pysm.State("stechen")

        self.add_state(idle, initial=True)
        self.add_state(stechen)

        idle.handlers = {
            "exit": self.idle_on_exit,
            "einwerfen": self.einwurf_handler,
            "wuerfeln": self.wuerfeln_handler,
        }

        stechen.handlers = {
            "stechen": self.stechen_handler,
            "einwerfen": self.raise_falsche_aktion,
            "wuerfeln": self.wuerfeln_handler,
        }

        self.add_transition(
            idle,
            stechen,
            events=["stechen"],
            action=None,
            condition=self.stechen_possible,
            after=self.stechen_handler,
        )

        self.initialize()

    def einwurf_handler(self, state, event):
        """Called when event "einwerfen" is dispatched"""
        spieler_name = event.cargo["spieler_name"]
        if spieler_name in [sp.name for sp in self.__spieler_liste]:
            raise FalscherSpieler

        spieler = Spieler(spieler_name)
        einwurf = wuerfel.werfen(1)[0]

        spieler.augen = einwurf
        self.__spieler_liste.append(spieler)

        roll_list = [sp.augen for sp in self.__spieler_liste]

        self.__stecher_liste = [
            sp for sp in self.__spieler_liste if sp.augen == min(roll_list)
        ]
        self.__stecher_count = len(self.__stecher_liste)

    def stechen_handler(self, state, event):
        spieler_name = event.cargo["spieler_name"]
        if len(self.__gestochen_liste) == 0:
            self._init_stecher_count = len(self.__stecher_liste)

        # check if already gestochen
        if spieler_name in [pl.name for pl in self.__gestochen_liste]:
            raise FalscherSpieler

        # check if eligible
        if spieler_name not in [st.name for st in self.stecher_liste]:
            raise FalscherSpieler

        stich = wuerfel.werfen(1)[0]
        stecher = [sp for sp in self.__spieler_liste if sp.name == spieler_name][0]
        stecher.augen = stich

        self.__gestochen_liste.append(stecher)
        # if all stiche done, determine starting player or stech again
        if len(self.__gestochen_liste) == self._init_stecher_count:
            stich_list = [st.augen for st in self.__gestochen_liste]
            self.__stecher_liste = [
                sp for sp in self.__gestochen_liste if sp.augen == min(stich_list)
            ]
            self.__gestochen_liste = []
            # sort stecher by stich
        elif len(self.__gestochen_liste) < self._init_stecher_count:
            pass

        self.__stecher_count = len(self.__stecher_liste)

    def wuerfeln_handler(self, state, event):
        spieler_name = event.cargo["spieler_name"]
        if not self.wuerfeln_possible():
            raise FalscheAktion
        elif spieler_name != self.__stecher_liste[0].name:
            raise FalscherSpieler

    def raise_falsche_aktion(self, state, event):
        raise FalscheAktion

    def idle_on_exit(self, state, event):
        pass

    def stechen_possible(self, state, event):
        if len(self.__spieler_liste) > 1 and self.__stecher_count > 1:
            return True
        else:
            raise FalscheAktion

    def wuerfeln_possible(self):
        return len(self.__spieler_liste) > 1 and self.__stecher_count <= 1

    def sortierte_spieler_liste(self):
        spieler_liste = self.__spieler_liste
        if self.state.name == "stechen":
            # rotate spieler_liste according to lowest stecher
            spieler = self.__stecher_liste[0]
            idx = self.__spieler_liste.index(spieler)
            spieler_liste = spieler_liste[idx:] + spieler_liste[:idx]
        else:
            # rotate spieler_liste such that lowest roll is first element
            roll_list = [sp.augen for sp in spieler_liste]
            min_roll = min(roll_list)
            min_index = roll_list.index(min_roll)
            spieler_liste = spieler_liste[min_index:] + spieler_liste[:min_index]
        return spieler_liste


class Halbzeit(pysm.StateMachine):
    def __init__(self):
        super().__init__("Halbzeit")
        self.__aktiver_spieler = None
        self.__verlierende = None
        self.__spielzeit_status = None
        self.__rdm = None
        self.letzter_wurf = [None, None, None]

        wuerfeln = pysm.State("wuerfeln")
        wuerfeln.handlers = {
            "wuerfeln": self.wuerfeln_handler,
            "beiseite_legen": self.beiseite_legen_handler,
            "weiter": self.naechster_spieler_handler,
        }
        self.add_state(wuerfeln, initial=True)

        self.initialize()

    def starten(self, state, event):
        vorheriger_state = self.root_machine.state_stack.peek()
        spieler_liste = vorheriger_state.sortierte_spieler_liste()

        self.__initiale_spieler = spieler_liste.copy()
        self.__aktiver_spieler = spieler_liste[0]
        self.__spielzeit_status = SpielzeitStatus(15, spieler_liste)
        self.__rdm = RundenDeckelManagement(self.__spielzeit_status)

    @property
    def spieler_liste(self):
        return self.spielzeit_status.spieler

    def sortierte_spieler_liste(self):
        if not self.__verlierende:
            raise DuHastMistGebaut("Es gibt noch keinen definierten Startspieler")
        for idx, spieler in enumerate(self.__initiale_spieler):
            if spieler.name == self.__verlierende.name:
                break
        else:
            raise DuHastMistGebaut(
                f"Der/die Verlierende `{self.__verlierende.name}`)` spielt gar nicht "
                f"mit! Mitspielende: {self.__initiale_spieler}"
            )
        sotiert = self.__initiale_spieler[idx:] + self.__initiale_spieler[:idx]
        return sotiert

    def wuerfeln_handler(self, state, event):
        spieler = self.aktiver_spieler
        spieler_name = event.cargo["spieler_name"]

        if spieler_name != spieler.name:
            raise FalscherSpieler(
                f"{spieler_name} hat geworfen, "
                f"{self.aktiver_spieler.name} war aber dran!"
            )

        # first throw (always 3 dice)
        if spieler.anzahl_wuerfe == 0:
            spieler.augen = wuerfel.werfen(3)
            spieler.anzahl_wuerfe += 1
            self.rdm.wurf(spieler_name, spieler.augen, aus_der_hand=True)
        elif spieler.anzahl_wuerfe < self.rdm.num_maximale_würfe:
            spieler.augen = wuerfel.werfen(3)
            spieler.anzahl_wuerfe += 1
            self.rdm.wurf(spieler_name, spieler.augen, aus_der_hand=True)
        else:
            # AUF SEMANTIK ACHTEN (SPRECHT GUTES DEUTSCH IHR HURENSÖHNE)
            num_wurf = self.rdm.num_maximale_würfe
            plural_switch = "Wurf ist" if num_wurf == 1 else "Würfe sind"
            zahl_zu_wort = {1: "ein", 2: "zwei", 3: "drei"}
            meldung = (
                f"Maximal {zahl_zu_wort[num_wurf]} {plural_switch} erlaubt, "
                f"{spieler.name}!"
            )
            raise ZuOftGeworfen(meldung)

    def beiseite_legen_handler(self, state, event):
        pass

    def naechster_spieler_handler(self, state, event):
        self.rdm.weiter()
        self.spieler_liste = self.spieler_liste[1:] + self.spieler_liste[:1]
        self.aktiver_spieler = self.spieler_liste[0]

    def beendet(self):
        return len(self.spieler_liste) == 1


class SchockenRunde(pysm.StateMachine):
    def __init__(self):
        super().__init__("SchockenRunde")
        self.einwerfen = Einwerfen()
        self.halbzeit_erste = Halbzeit()
        self.halbzeit_zweite = Halbzeit()
        self.finale = Halbzeit()
        anstoßen = pysm.State("anstoßen!")

        # add states to machine
        self.add_state(self.einwerfen, initial=True)
        self.add_state(self.halbzeit_erste)
        self.add_state(self.halbzeit_zweite)
        self.add_state(self.finale)
        self.add_state(anstoßen)

        self.add_transition(
            self.einwerfen,
            self.halbzeit_erste,
            events=[events.WÜRFELN],
            after=self.halbzeit_erste.starten,
        )

        self.add_transition(
            self.halbzeit_erste,
            self.halbzeit_zweite,
            events=[events.FERTIG_HALBZEIT],
            after=self.halbzeit_zweite.starten,
        )
        self.add_transition(
            self.halbzeit_zweite,
            self.finale,
            events=[events.FERTIG_HALBZEIT],
            after=self.finale.starten,
        )
        self.add_transition(
            self.finale, anstoßen, events=[events.FERTIG_HALBZEIT], after=self.anstoßen,
        )
        self.initialize()

    def command_to_event(self, spieler_name, command):
        if command == "einwerfen":
            event = pysm.Event("einwerfen", spieler_name=spieler_name)
        elif command == "wuerfeln":
            event = pysm.Event("wuerfeln", spieler_name=spieler_name)
        elif command == "stechen":
            event = pysm.Event("stechen", spieler_name=spieler_name)
        elif command == "weiter":
            event = pysm.Event("weiter", spieler_name=spieler_name)
        elif command == "beiseite legen":
            event = pysm.Event("beiseite legen", spieler_name=spieler_name)
        else:
            raise FalscheAktion
        self.dispatch(event)

    def anstoßen(self, state, event):
        print("PROST!")
