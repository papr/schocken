from pysm import StateMachine, State, Event
from .spieler import Spieler
from .wuerfel import werfen
from .exceptions import FalscheAktion, FalscherSpieler

class Einwerfen(object):
    def __init__(self):
        self.sm = self.init_sm()
        self.spieler_liste = []
        self.stecher_count = 0
        self.stecher_liste = []
        self._gestochen_liste = []

    def init_sm(self):
        sm = StateMachine("Einwerfen")
        idle = State("erster_spieler_unbestimmt")
        stechen = State("stechen")
        fertig = State("fertig")
        
        sm.add_state(idle, initial = True)
        sm.add_state(stechen)
        sm.add_state(fertig)

        idle.handlers = {
                'exit' : self.idle_on_exit,
                'einwerfen': self.einwurf_handler,
                'wuerfeln': self.wuerfeln_handler,
                              }

        stechen.handlers = {
                'stechen': self.stechen_handler,
                'wuerfeln': self.wuerfeln_handler
                           }

        sm.add_transition(idle, stechen, 
                                 events=['stechen'],
                                 action=None,
                                 condition=self.stechen_possible,
                                 before=None,
                                 after=self.stechen_handler)

        sm.add_transition(idle, fertig, 
                                 events=['wuerfeln'],
                                 action=None,
                                 condition=self.wuerfeln_possible,
                                 before=None,
                                 after=None)

        sm.add_transition(stechen, fertig,
                                 events=['wuerfeln'],
                                 action=None,
                                 condition=self.wuerfeln_possible,
                                 before=None,
                                 after=None)

        sm.initialize()
        return sm 

    def einwurf_handler(self, state, event):
        """Called when event "einwerfen" is dispatched"""
        spieler_name = event.cargo["spieler_name"]
        if spieler_name in [sp.name for sp in self.spieler_liste]:
            raise FalscherSpieler
        spieler = Spieler(spieler_name)
        einwurf = werfen(1)[0]
#         if "stecher" in spieler_name:
            # einwurf = 1
        # else:
            # einwurf = 2

        spieler.augen = einwurf
        self.spieler_liste.append(spieler)
        # find smallest roll
        roll_list = [sp.augen for sp in self.spieler_liste]
        min_roll = min(roll_list)
        min_index = roll_list.index(min_roll)
        # rotate list such that lowest roll is first element
        self.spieler_liste = (
            self.spieler_liste[min_index:] + self.spieler_liste[:min_index]
        )
        # check if lowest roll only occurs once
        self.stecher_liste = [
            sp for sp in self.spieler_liste if sp.augen == min_roll
        ]
        self.stecher_count = len(self.stecher_liste)
        # self._gestochen_liste = []
        print(f"Spieler {spieler_name} wirft mit {spieler.augen} ein.")

    def stechen_handler(self, state, event):
        spieler_name = event.cargo["spieler_name"]
        if len(self._gestochen_liste) == 0:
            self._init_stecher_count = len(self.stecher_liste)

        # check if already gestochen
        if spieler_name in [pl.name for pl in self._gestochen_liste]:
            raise FalscherSpieler

        # check if eligible
        if spieler_name not in [st.name for st in self.stecher_liste]:
            raise FalscherSpieler

        stich = werfen(1)[0]
        # if "stecher" in spieler_name:
            # stich = 1
        # else:
            # stich = 2
        stecher = [sp for sp in self.spieler_liste if sp.name == spieler_name][0]
        stecher.augen = stich

        self._gestochen_liste.append(stecher)
        # self.stecher_liste = [
            # st for st in self.stecher_liste if st not in self._gestochen_liste
        # ]
        # if all stiche done, determine starting player or stech again
        if len(self._gestochen_liste) == self._init_stecher_count:
            stich_list = [st.augen for st in self._gestochen_liste]
            min_stich = min(stich_list)
            self.stecher_liste = [
                sp for sp in self._gestochen_liste if sp.augen == min_stich
            ]
            min_index = stich_list.index(min_stich)
            self.aktiver_spieler = self.spieler_liste[min_index]
            self._gestochen_liste = []
            # sort stecher by stich
        elif len(self._gestochen_liste) < self._init_stecher_count:
            pass

        print(f"{spieler_name} sticht mit {stecher.augen}")
        print(self.stecher_liste)
        self.stecher_count = len(self.stecher_liste)

    def wuerfeln_handler(self, state, event):
        spieler_name = event.cargo["spieler_name"]
        print(f"{spieler_name} will wuerfeln")
        if not self.wuerfeln_possible(state, event):
            raise FalscheAktion
        elif spieler_name != self.stecher_liste[0].name:
            raise FalscherSpieler

    def idle_on_exit(self, state, event):
        pass
    
    def stechen_possible(self, state, event):
        return len(self.spieler_liste) > 1 and self.stecher_count > 1

    def wuerfeln_possible(self, state, event):
        return len(self.spieler_liste) > 1 and self.stecher_count == 1
    
    @property
    def state(self):
        return self.sm.leaf_state.name


class SchockenRunde(object):
    def __init__(self):
        self.spieler_liste = []
        self.sm = self._init_sm()

    def _init_sm(self):
        sm = StateMachine("SchockenRunde")
        
        einwerfen = Einwerfen()

        # add states to machine
        sm.add_state(einwerfen.sm, initial = True)

        sm.initialize()
        return sm

    def command_to_event(self, spieler_name, command):
        if command == "einwerfen":
            event = Event("einwerfen", spieler_name=spieler_name)
        elif command == "wuerfeln":
            event = Event("wuerfeln", spieler_name=spieler_name)

        self.sm.dispatch(event)

    @property
    def state(self):
        return self.sm.leaf_state.name

    
    
if __name__ == "__main__":
    sr = SchockenRunde()

