import sublime, sublime_plugin

from ..flow import FlowProject, panel

print('flow / load set build target')

class FlowSetTargetBuild( sublime_plugin.WindowCommand ):
    def run(self):
        view = self.window.active_view()
        panel(self.window, FlowProject.flow.get_targets(), self.on_target_select, 0, 1)

    def on_target_select(self, index):
        if index > 0:
            FlowProject.flow.set_flow_target_by_index(index)

    def is_visible(self):
        view = self.window.active_view()
        pt = view.sel()[0].b
        scope = view.scope_name(pt)
        if "source.flow" in scope:
            if FlowProject.flow.flow_file:
                return True

        return False

