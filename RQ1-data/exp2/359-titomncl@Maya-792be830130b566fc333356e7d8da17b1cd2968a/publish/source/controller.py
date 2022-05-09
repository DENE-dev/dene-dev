from qtpy.QtWidgets import QWidget as Qw

from Maya.publish.source.core import filepath

class Controller(object):

    def __init__(self, ui, parent=None):

        self.filepath = filepath()

        self.ui = ui(self, parent)

        self.first_save_or_not()

    def first_save_or_not(self):
        if not self.filepath:
            self.show()
        else:
            choice, save_choice = self.ui.message_box()

            if choice == save_choice:
                self.save_and_publish()

    def show(self):
        self.ui.show()

    def save_and_publish(self, first_save=False):
        if first_save:
            self.filepath = core.first_save("", "", "")
        else:
            self.filepath = core.save(self.filepath)

        core.publish(self.filepath)