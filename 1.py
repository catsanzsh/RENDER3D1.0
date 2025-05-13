from ursina import *
from ursina.prefabs.editor_camera import EditorCamera # For free-look debugging and navigation
import math
import time

# --- Configuration ---
WINDOW_WIDTH = 1280 # Increased for better view
WINDOW_HEIGHT = 720
GAME_TITLE = "Super Mario 3D World - Ursina Overworld (Enhanced 3D Vibe)"

# --- Level Data Structure ---
levels_data = [
    {"id": "1-1", "name": "World 1-1", "pos": (-6, 0.5, 0), "color": color.lime, "unlocks": ["1-2"], "initial_state": "unlocked"},
    {"id": "1-2", "name": "World 1-2", "pos": (-3, 0.5, 1.5), "color": color.green, "unlocks": ["1-A", "1-3"], "initial_state": "locked"},
    {"id": "1-A", "name": "World 1-A (Bonus)", "pos": (-3, 0.5, -2), "color": color.gold, "unlocks": [], "initial_state": "locked"}, # Bonus node
    {"id": "1-3", "name": "World 1-3", "pos": (0, 0.5, 1), "color": color.olive, "unlocks": ["1-Castle"], "initial_state": "locked"}, # Changed color.dark_green to color.olive
    {"id": "1-Castle", "name": "World 1-Castle", "pos": (3, 0.5, 0), "color": color.red, "unlocks": ["2-1"], "initial_state": "locked"}, # Example of unlocking next world
    {"id": "2-1", "name": "World 2-1", "pos": (6, 0.5, 0), "color": color.blue, "unlocks": [], "initial_state": "locked"},
]

class LevelNode(Button):
    def __init__(self, level_data, on_node_click_func):
        super().__init__(
            parent=scene,
            model='sphere',
            color=level_data['color'],
            position=(level_data['pos'][0], level_data['pos'][1], level_data['pos'][2]), # x, y, z
            scale=0.8,
            highlight_color=color.cyan, # Mouse hover highlight
            pressed_color=color.azure
        )
        self.level_id = level_data['id']
        self.level_name = level_data['name']
        self.unlocks = level_data['unlocks']
        self.initial_color = level_data['color']
        self.node_state = level_data.get('initial_state', 'locked') # 'locked', 'unlocked', 'completed'
        
        self.tooltip_text_format = f"{self.level_id}: {self.level_name}\nState: {{}}"
        # Ensure tooltip is created after self.level_id and self.level_name are set
        self.tooltip = Tooltip(self.tooltip_text_format.format(self.node_state.capitalize()), parent=self, origin=(0,-1.5), background_color=color.black66, enabled=False)
        # self.tooltip.enabled = False # Initially hidden, enabled on hover by Button (already set in Tooltip constructor)


        self.label_base_scale = 3
        self.label = Text(
            text=self.level_id,
            parent=self,
            origin=(0,0),
            scale=self.label_base_scale / self.scale_x, # Adjust based on parent's scale
            z=-0.6, # In front of the sphere's surface
            color=color.black,
            billboard=True # Always faces the camera
        )

        self.on_click_func = on_node_click_func
        
        self.original_y = self.position.y
        self.is_current_game_node = False
        self.is_bonus_node = (self.initial_color == color.gold)
        self.is_castle_node = "Castle" in self.level_id

        if self.is_castle_node:
            # Simple castle tower on top of the sphere
            Entity(
                parent=self,
                model='cone', 
                color=color.dark_gray, # Changed from color.dark_grey to color.dark_gray for consistency
                scale=(0.7, 0.5, 0.7), # Relative to parent sphere
                position=(0, self.scale_y * 0.5, 0), # Position on top
                rotation_x=-90 # Pointing upwards
            )
            # Add a small flag
            Entity(
                parent=self,
                model='quad',
                color=color.red,
                scale=(0.2, 0.3, 0.1),
                position=(0, self.scale_y * 0.5 + 0.25, -0.05), # Above cone
                billboard=True
            )


    def on_click(self):
        """Called by Ursina when the button is clicked."""
        if self.on_click_func:
            self.on_click_func(self)

    def set_state(self, new_state):
        """Sets the node's state and updates its tooltip."""
        self.node_state = new_state
        if self.tooltip: # Check if tooltip exists
            self.tooltip.text = self.tooltip_text_format.format(self.node_state.capitalize())
        # Visual update will be handled by update_visual_state called from main game logic

    def update_visual_state(self, is_current=False):
        """Updates the node's appearance based on its state and if it's the current node."""
        self.is_current_game_node = is_current
        base_scale_value = 0.8
        current_indicator_scale_multiplier = 1.25
        locked_scale_multiplier = 0.7

        target_scale_vec = Vec3(base_scale_value, base_scale_value, base_scale_value) # Renamed to avoid conflict

        if self.node_state == 'locked':
            self.color = color.gray
            target_scale_vec *= locked_scale_multiplier
            if hasattr(self, 'collider') and self.collider is not None: # Check if collider exists before trying to set it
                self.collider = None # Disable clicking on locked nodes
        elif self.node_state == 'unlocked':
            self.color = self.initial_color
            if not hasattr(self, 'collider') or self.collider is None: # Check before setting
                 self.collider = 'sphere' # Enable clicking
        elif self.node_state == 'completed': # Visually distinct if needed
            self.color = color.color(self.initial_color.h, self.initial_color.s, self.initial_color.v * 0.7, self.initial_color.a) # Darker shade
            if not hasattr(self, 'collider') or self.collider is None: # Check before setting
                self.collider = 'sphere' # Still clickable to revisit? Or set to None.

        if is_current:
            self.color = color.white # Make current node pop
            target_scale_vec *= current_indicator_scale_multiplier
        
        # Smoothly animate scale changes
        self.animate_scale(target_scale_vec, duration=0.2) # Use renamed variable
        
        # Update label scale - ensure it's done after parent scale might change
        # The label is parented, so its scale is relative.
        # If self.scale changes, label's world scale changes. We want label to have consistent apparent size.
        # self.label.scale = self.label_base_scale / target_scale_vec.x # This keeps label size constant relative to node
        # To keep label size more constant on screen:
        self.label.world_scale = self.label_base_scale * 0.1 # Adjust this factor for desired screen size


    def update(self):
        """Called every frame by Ursina."""
        # Bobbing animation for the current node
        if self.is_current_game_node:
            # Ensure original_y is not None before using it
            if self.original_y is not None:
                 self.y = self.original_y + math.sin(time.time() * 3) * 0.15 # Bobbing effect
            else: # Fallback if original_y was not set (should not happen with current __init__)
                 self.y = self.position.y + math.sin(time.time() * 3) * 0.15


        # Spinning animation for bonus nodes
        if self.is_bonus_node and self.node_state != 'locked':
            self.rotation_y += 60 * time.dt # Spin speed

        # Keep label facing camera (billboard=True handles rotation, but ensure position is correct)
        # self.label.world_rotation = camera.world_rotation


# --- Main Game Logic ---
app = Ursina(title=GAME_TITLE, borderless=False, fullscreen=False, window_size=(WINDOW_WIDTH, WINDOW_HEIGHT))

# --- Scene Setup ---
Sky(texture='sky_sunset') # Use a built-in sky texture for vibe
ground = Entity(model='plane', collider='box', scale=40, color=color.rgb(50, 180, 50), texture='white_cube', texture_scale=(20,20))
if ground.texture: # Check if texture exists before setting filtering
    ground.texture.filtering = None # Pixelated look for ground if desired, or leave for smooth

# --- Lighting ---
sun = DirectionalLight(y=2, z=3, shadows=True)
AmbientLight(color=color.rgba(100, 100, 100, 0.1))

# --- Camera ---
# Using EditorCamera for easy navigation.
# You can customize camera position and behavior further.
camera.position = (0, 15, -15) # Initial camera position, looking down a bit
camera.rotation_x = 30 # Angled view
editor_camera = EditorCamera(enabled=True, ignore_paused=True)


# --- Game State Variables ---
all_level_nodes = {} # Dictionary to store LevelNode instances by ID
paths_entities = {} # To store path line entities: key (node1_id, node2_id)

current_player_node_id = None

# --- Functions ---
def setup_level_nodes_and_paths():
    """Creates all level nodes and the paths connecting them."""
    global current_player_node_id

    # Create nodes
    for data in levels_data:
        node = LevelNode(level_data=data, on_node_click_func=handle_node_click)
        all_level_nodes[data['id']] = node
        if data['initial_state'] == 'unlocked' and current_player_node_id is None:
            current_player_node_id = data['id']

    # Create paths
    for node_id, node in all_level_nodes.items():
        for target_id in node.unlocks:
            if target_id in all_level_nodes:
                target_node = all_level_nodes[target_id]
                path_key = tuple(sorted((node_id, target_id))) # Unique key for each path

                if path_key not in paths_entities:
                    # Use Line for paths
                    # Ensure node.position and target_node.position are valid Vec3
                    if isinstance(node.position, Vec3) and isinstance(target_node.position, Vec3):
                        line_entity = Entity(parent=scene, model=Mesh(vertices=[node.position, target_node.position], mode='line', thickness=5))
                        paths_entities[path_key] = line_entity
                    else:
                        print(f"Error: Invalid position for node {node_id} or {target_id} when creating path.")
            else:
                print(f"Warning: Node '{node_id}' tries to unlock non-existent node '{target_id}'")
    
    if current_player_node_id is None and levels_data:
        current_player_node_id = levels_data[0]['id'] # Fallback to first node if none are 'unlocked'
        if current_player_node_id and current_player_node_id in all_level_nodes: # Check if node exists
             all_level_nodes[current_player_node_id].set_state('unlocked')


    update_all_visuals()


def update_path_visuals():
    """Updates the visual appearance of paths based on connected node states."""
    for (id1, id2), path_entity in paths_entities.items():
        node1 = all_level_nodes.get(id1)
        node2 = all_level_nodes.get(id2)

        if not node1 or not node2:
            continue
        
        # Ensure path_entity has a model before trying to access its thickness or color
        if not hasattr(path_entity, 'model') or path_entity.model is None:
            continue


        # Path is visible if either node is unlocked or completed,
        # and more prominent if it's a path from/to the current node or an unlocked path.
        is_node1_accessible = node1.node_state in ['unlocked', 'completed'] or node1.is_current_game_node
        is_node2_accessible = node2.node_state in ['unlocked', 'completed'] or node2.is_current_game_node
        
        # Path is active if it connects two non-locked nodes, or one is current
        path_active = (node1.node_state != 'locked' and node2.node_state != 'locked')

        if path_active:
            if node1.is_current_game_node or node2.is_current_game_node:
                path_entity.color = color.white # Highlight path connected to current node
                path_entity.model.thickness = 8
            elif node1.node_state == 'unlocked' and node2.node_state == 'unlocked': # Both ends are simply unlocked
                 path_entity.color = color.light_gray # Unlocked path
                 path_entity.model.thickness = 5
            elif node1.node_state == 'completed' and node2.node_state == 'unlocked' or \
                 node1.node_state == 'unlocked' and node2.node_state == 'completed' or \
                 node1.node_state == 'completed' and node2.node_state == 'completed': # Path between completed/unlocked
                 path_entity.color = color.gray # Slightly dimmer for established paths
                 path_entity.model.thickness = 5
            else: # Path to a locked node from an unlocked one (should not happen if path_active is true and logic is correct)
                 path_entity.color = color.dark_gray 
                 path_entity.model.thickness = 3

            path_entity.visible = True
        else: # Path involving at least one locked node that isn't made active by the other end being current
            path_entity.color = color.black # Barely visible or just off
            path_entity.model.thickness = 3
            # Show path if one end is accessible (e.g. an unlocked node leading to a still-locked node)
            path_entity.visible = (is_node1_accessible or is_node2_accessible) and not (node1.node_state == 'locked' and node2.node_state == 'locked')


def update_all_visuals():
    """Updates the visual state of all nodes and paths."""
    for node_id, node in all_level_nodes.items():
        is_current = (node_id == current_player_node_id)
        node.update_visual_state(is_current=is_current)
    update_path_visuals()


def set_current_player_node(target_node_id):
    """Moves the player to the target node and updates game state."""
    global current_player_node_id
    
    if current_player_node_id and current_player_node_id in all_level_nodes:
        prev_node = all_level_nodes[current_player_node_id]
        if prev_node.node_state == 'unlocked': 
             prev_node.set_state('completed') 

    current_player_node_id = target_node_id
    
    current_node = all_level_nodes.get(target_node_id)
    if current_node:
        if current_node.node_state == 'locked': # Should not happen if click logic is correct
            current_node.set_state('unlocked') # Ensure it's at least unlocked if we somehow land on a locked one

        for unlock_target_id in current_node.unlocks:
            if unlock_target_id in all_level_nodes:
                node_to_unlock = all_level_nodes[unlock_target_id]
                if node_to_unlock.node_state == 'locked':
                    node_to_unlock.set_state('unlocked')
                    # Small animation for unlocking
                    # Check if node_to_unlock is not None before animating
                    if node_to_unlock:
                        original_scale = node_to_unlock.scale
                        pop_scale = original_scale * 1.5
                        
                        node_to_unlock.animate_scale(pop_scale, duration=0.2, curve=curve.out_bounce)
                        # Schedule the return to original scale after the pop animation
                        invoke(node_to_unlock.animate_scale, original_scale, delay=0.21, duration=0.1)


    update_all_visuals()
    
    # Optional: Camera focus on new node
    # if current_player_node_id and current_player_node_id in all_level_nodes:
    #    camera.animate_position(all_level_nodes[current_player_node_id].world_position + Vec3(0, 5, -5), duration=0.5)


def handle_node_click(clicked_node: LevelNode):
    """Handles logic when a level node is clicked."""
    if not isinstance(clicked_node, LevelNode): # Type check
        print("Error: handle_node_click received non-LevelNode object")
        return

    print(f"Clicked: {clicked_node.level_id}, State: {clicked_node.node_state}")

    if clicked_node.node_state == 'locked':
        print(f"Node {clicked_node.level_id} is locked.")
        clicked_node.shake(duration=0.3, magnitude=0.05, speed=20) # Adjusted shake
        return

    if clicked_node.level_id == current_player_node_id:
        print(f"Already at {clicked_node.level_id}. Consider this 'entering the level'.")
        # Placeholder for entering the level
        Text(
            f"Entering Level: {clicked_node.level_name}",
            origin=(0,0), scale=2, color=color.yellow, background=True, duration=2
        )
        return

    # Check if the clicked node is directly unlockable from the current node
    # This makes movement more restrictive to defined paths
    can_move = False
    if current_player_node_id and current_player_node_id in all_level_nodes:
        player_node = all_level_nodes[current_player_node_id]
        if clicked_node.level_id in player_node.unlocks and clicked_node.node_state == 'unlocked':
            can_move = True
        elif clicked_node.node_state == 'unlocked' or clicked_node.node_state == 'completed': # Allow moving to any unlocked/completed node
             # This makes it less restrictive, player can jump around.
             # For more Mario-like progression, you'd only allow movement to adjacent unlocked nodes.
             # For now, let's keep it simple: if it's unlocked, you can go.
             can_move = True


    if not can_move and clicked_node.node_state != 'unlocked' and clicked_node.node_state != 'completed':
        print(f"Cannot move to {clicked_node.level_id} from {current_player_node_id} yet or it's not unlocked.")
        clicked_node.shake(duration=0.3, magnitude=0.05, speed=20)
        return
    
    print(f"Moving to {clicked_node.level_id}")
    set_current_player_node(clicked_node.level_id)
    
    Text(
        f"Moved to: {clicked_node.level_name}",
        origin=(0,0), scale=2, color=color.lime, background=True, duration=2
    )


# --- Initialize Game ---
if __name__ == '__main__':
    setup_level_nodes_and_paths()
    
    # Small instruction text
    Text(
        "Right-Click + Drag to Pan, Scroll to Zoom, Middle-Click + Drag to Orbit\nClick nodes to move.",
        position=window.top_left + Vec2(0.01, -0.01), # Adjusted y for two lines
        scale=0.9,
        color=color.white,
        background=True,
        background_color=color.black66,
        parent=camera.ui # Make it part of UI so it doesn't move with camera
    )
    app.run()
