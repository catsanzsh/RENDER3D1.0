from ursina import *
from ursina.prefabs.editor_camera import EditorCamera
import math
import time

# --- Configuration ---
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
GAME_TITLE = "Super Mario 3D World - Ursina Overworld"

# --- Level Data Structure ---
levels_data = [
    {"id": "1-1", "name": "World 1-1", "pos": (-6, 0.5, 0), "color": color.lime, "unlocks": ["1-2"], "initial_state": "unlocked"},
    {"id": "1-2", "name": "World 1-2", "pos": (-3, 0.5, 1.5), "color": color.green, "unlocks": ["1-A", "1-3"], "initial_state": "locked"},
    {"id": "1-A", "name": "World 1-A (Bonus)", "pos": (-3, 0.5, -2), "color": color.gold, "unlocks": [], "initial_state": "locked"},
    {"id": "1-3", "name": "World 1-3", "pos": (0, 0.5, 1), "color": color.olive, "unlocks": ["1-Castle"], "initial_state": "locked"},
    {"id": "1-Castle", "name": "World 1-Castle", "pos": (3, 0.5, 0), "color": color.red, "unlocks": ["2-1"], "initial_state": "locked"},
    {"id": "2-1", "name": "World 2-1", "pos": (6, 0.5, 0), "color": color.blue, "unlocks": [], "initial_state": "locked"},
]

# --- Level Node Class ---
class LevelNode(Button):
    def __init__(self, level_data, on_node_click_func):
        super().__init__(
            parent=scene,
            model='sphere',
            color=level_data['color'],
            position=(level_data['pos'][0], level_data['pos'][1], level_data['pos'][2]),
            scale=0.8,
            highlight_color=color.cyan,
            pressed_color=color.azure
        )
        self.level_id = level_data['id']
        self.level_name = level_data['name']
        self.unlocks = level_data['unlocks']
        self.initial_color = level_data['color']
        self.node_state = level_data.get('initial_state', 'locked')

        self.tooltip = Tooltip(
            f"{self.level_id}: {self.level_name}\nState: {self.node_state.capitalize()}",
            parent=self,
            origin=(0, -1.5),
            background_color=color.black66,
            enabled=False
        )

        self.label = Text(
            text=self.level_id,
            parent=self,
            origin=(0, 0),
            scale=3 / self.scale_x,
            z=-0.6,
            color=color.black,
            billboard=True
        )

        self.on_click_func = on_node_click_func
        self.original_y = self.position.y
        self.is_current_game_node = False
        self.is_bonus_node = (self.initial_color == color.gold)
        self.is_castle_node = "Castle" in self.level_id

        if self.is_castle_node:
            Entity(parent=self, model='cone', color=color.dark_gray, scale=(0.7, 0.5, 0.7), position=(0, self.scale_y * 0.5, 0), rotation_x=-90)
            Entity(parent=self, model='quad', color=color.red, scale=(0.2, 0.3, 0.1), position=(0, self.scale_y * 0.5 + 0.25, -0.05), billboard=True)

    def on_click(self):
        if self.on_click_func:
            self.on_click_func(self)

    def set_state(self, new_state):
        self.node_state = new_state
        self.tooltip.text = f"{self.level_id}: {self.level_name}\nState: {self.node_state.capitalize()}"

    def update_visual_state(self, is_current=False):
        self.is_current_game_node = is_current
        base_scale = 0.8
        target_scale = Vec3(base_scale, base_scale, base_scale)

        if self.node_state == 'locked':
            self.color = color.gray
            target_scale *= 0.7
            self.collider = None
        elif self.node_state == 'unlocked':
            self.color = self.initial_color
            self.collider = 'sphere'
        elif self.node_state == 'completed':
            self.color = color.color(self.initial_color.h, self.initial_color.s, self.initial_color.v * 0.7)
            self.collider = 'sphere'

        if is_current:
            self.color = color.white
            target_scale *= 1.25

        self.animate_scale(target_scale, duration=0.2)
        self.label.world_scale = 0.3

    def update(self):
        if self.is_current_game_node:
            self.y = self.original_y + math.sin(time.time() * 3) * 0.15
        if self.is_bonus_node and self.node_state != 'locked':
            self.rotation_y += 60 * time.dt

# --- Main Game Logic ---
app = Ursina(title=GAME_TITLE, borderless=False, fullscreen=False, window_size=(WINDOW_WIDTH, WINDOW_HEIGHT))

# --- Scene Setup ---
Sky(texture='sky_sunset')
ground = Entity(model='plane', collider='box', scale=40, color=color.rgb(50, 180, 50), texture=None)

sun = DirectionalLight(y=2, z=3, shadows=True)
AmbientLight(color=color.rgba(100, 100, 100, 0.1))

camera.position = (0, 15, -15)
camera.rotation_x = 30
editor_camera = EditorCamera(enabled=True, ignore_paused=True)

# --- Main Menu Setup ---
main_menu_panel = Entity(parent=camera.ui, enabled=True)
title_text = Text(
    text=GAME_TITLE,
    parent=main_menu_panel,
    scale=2,
    origin=(0, 0),
    position=(0, 0.3),
    color=color.yellow
)
start_button = Button(
    parent=main_menu_panel,
    text='Start Game',
    scale=0.1,
    color=color.green,
    highlight_color=color.lime,
    position=(0, 0.1),
    origin=(0, 0),
    on_click=lambda: start_game()
)
quit_button = Button(
    parent=main_menu_panel,
    text='Quit',
    scale=0.1,
    color=color.red,
    highlight_color=color.orange,
    position=(0, -0.1),
    origin=(0, 0),
    on_click=application.quit
)

# --- Game State Variables ---
all_level_nodes = {}
paths_entities = {}
current_player_node_id = None

# --- Functions ---
def start_game():
    main_menu_panel.enabled = False
    setup_level_nodes_and_paths()

def setup_level_nodes_and_paths():
    global current_player_node_id
    for data in levels_data:
        node = LevelNode(level_data=data, on_node_click_func=handle_node_click)
        all_level_nodes[data['id']] = node
        if data['initial_state'] == 'unlocked' and not current_player_node_id:
            current_player_node_id = data['id']

    for node_id, node in all_level_nodes.items():
        for target_id in node.unlocks:
            if target_id in all_level_nodes:
                path_key = tuple(sorted((node_id, target_id)))
                if path_key not in paths_entities:
                    paths_entities[path_key] = Entity(
                        parent=scene,
                        model=Mesh(vertices=[node.position, all_level_nodes[target_id].position], mode='line', thickness=5)
                    )

    if not current_player_node_id and levels_data:
        current_player_node_id = levels_data[0]['id']
        all_level_nodes[current_player_node_id].set_state('unlocked')

    update_all_visuals()

def update_path_visuals():
    for (id1, id2), path_entity in paths_entities.items():
        node1 = all_level_nodes[id1]
        node2 = all_level_nodes[id2]
        path_active = node1.node_state != 'locked' and node2.node_state != 'locked'

        if path_active:
            if node1.is_current_game_node or node2.is_current_game_node:
                path_entity.color = color.white
                path_entity.model.thickness = 8
            elif node1.node_state == 'unlocked' and node2.node_state == 'unlocked':
                path_entity.color = color.light_gray
                path_entity.model.thickness = 5
            else:
                path_entity.color = color.gray
                path_entity.model.thickness = 5
            path_entity.visible = True
        else:
            path_entity.color = color.black
            path_entity.model.thickness = 3
            path_entity.visible = node1.node_state in ['unlocked', 'completed'] or node2.node_state in ['unlocked', 'completed']

def update_all_visuals():
    for node_id, node in all_level_nodes.items():
        node.update_visual_state(is_current=(node_id == current_player_node_id))
    update_path_visuals()

def set_current_player_node(target_node_id):
    global current_player_node_id
    if current_player_node_id:
        prev_node = all_level_nodes[current_player_node_id]
        if prev_node.node_state == 'unlocked':
            prev_node.set_state('completed')

    current_player_node_id = target_node_id
    current_node = all_level_nodes[target_node_id]
    if current_node.node_state == 'locked':
        current_node.set_state('unlocked')
    for unlock_id in current_node.unlocks:
        if unlock_id in all_level_nodes and all_level_nodes[unlock_id].node_state == 'locked':
            all_level_nodes[unlock_id].set_state('unlocked')
            all_level_nodes[unlock_id].animate_scale(1.2, duration=0.2, curve=curve.out_bounce)
            invoke(all_level_nodes[unlock_id].animate_scale, 0.8, delay=0.21, duration=0.1)

    update_all_visuals()

def get_adjacent_nodes(node_id):
    adjacent = []
    for (id1, id2) in paths_entities.keys():
        if id1 == node_id:
            adjacent.append(id2)
        elif id2 == node_id:
            adjacent.append(id1)
    return adjacent

def handle_node_click(clicked_node):
    if clicked_node.node_state == 'locked':
        clicked_node.shake(duration=0.3, magnitude=0.05)
        return

    if clicked_node.level_id == current_player_node_id:
        Text(f"Entering Level: {clicked_node.level_name}", origin=(0, 0), scale=2, color=color.yellow, background=True, duration=2)
        return

    adjacent_nodes = get_adjacent_nodes(current_player_node_id)
    if clicked_node.level_id in adjacent_nodes and clicked_node.node_state in ['unlocked', 'completed']:
        set_current_player_node(clicked_node.level_id)
        Text(f"Moved to: {clicked_node.level_name}", origin=(0, 0), scale=2, color=color.lime, background=True, duration=2)
    else:
        clicked_node.shake(duration=0.3, magnitude=0.05)

# --- Instruction Text ---
Text(
    "Right-Click + Drag to Pan, Scroll to Zoom, Middle-Click + Drag to Orbit\nClick nodes to move.",
    position=window.top_left + Vec2(0.01, -0.01),
    scale=0.9,
    color=color.white,
    background=True,
    background_color=color.black66,
    parent=camera.ui
)

# --- Run the Game ---
app.run()
