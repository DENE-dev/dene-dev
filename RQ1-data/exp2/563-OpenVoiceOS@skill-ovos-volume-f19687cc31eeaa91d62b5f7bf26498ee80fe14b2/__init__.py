from os.path import dirname, join

from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill, intent_handler, intent_file_handler
from mycroft.util import play_wav
from mycroft.util.parse import extract_number
from ovos_utils.sound.alsa import AlsaControl


class VolumeSkill(MycroftSkill):
    def __init__(self):
        super(VolumeSkill, self).__init__("VolumeSkill")
        self.volume_sound = join(dirname(__file__), "blop-mark-diangelo.wav")

    def get_intro_message(self):
        # just pretend this method is called "on first boot"
        # will only run once when the skill is loaded for the first time
        self.set_volume(50)

    def set_volume(self, percent=None):
        volume = int(percent)
        volume = min(100, volume)
        volume = max(0, volume)
        AlsaControl().set_volume_percent(volume)
        play_wav(self.volume_sound)

    def increase_volume(self, volume_change=None):
        if not volume_change:
            volume_change = 15
        AlsaControl().increase_volume(volume_change)
        play_wav(self.volume_sound)

    def decrease_volume(self, volume_change=None):
        if not volume_change:
            volume_change = -15
        if volume_change > 0:
            volume_change = 0 - volume_change
        AlsaControl().increase_volume(volume_change)
        play_wav(self.volume_sound)

    @intent_handler(IntentBuilder("change_volume").require('change_volume'))
    def handle_change_volume_intent(self, message):
        utterance = message.data['utterance']
        volume_change = extract_number(normalize(utterance))
        self.set_volume(volume_change)
        if volume_change == 100:
            self.speak_dialog('max.volume')
        else:
            self.speak_dialog('set.volume.percent',
                              data={'level': volume_change})

    @intent_handler(IntentBuilder("less_volume").require('less_volume'))
    def handle_less_volume_intent(self, message):
        utterance = message.data['utterance']
        volume_change = extract_number(normalize(utterance))
        if volume_change > 0:
            volume_change = 0 - volume_change
        self.decrease_volume(volume_change)

    @intent_handler(
        IntentBuilder("increase_volume").require('increase_volume'))
    def handle_increase_volume_intent(self, message):
        utterance = message.data['utterance']
        volume_change = extract_number(normalize(utterance))
        self.increase_volume(volume_change)

    @intent_file_handler('max_volume.intent')
    def handle_max_volume_intent(self, message):
        self.set_volume(100)
        self.speak_dialog('max.volume')

    @intent_file_handler('high_volume.intent')
    def handle_high_volume_intent(self, message):
        self.set_volume(85)

    @intent_file_handler('default_volume.intent')
    def handle_default_volume_ntent(self, message):
        self.set_volume(70)

    @intent_file_handler('low_volume.intent')
    def handle_low_volume_intent(self, message):
        self.set_volume(30)

    @intent_handler(IntentBuilder("current_volume").require('current_volume'))
    def handle_query_volume(self, message):
        volume = AlsaControl().get_volume()
        self.speak_dialog('volume.is', data={'volume': volume})


def create_skill():
    return VolumeSkill()