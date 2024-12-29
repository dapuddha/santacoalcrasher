from settings import *
from math import sin
import os

# Get the absolute path to the game root directory
GAME_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class Model:
    def __init__(self, model, pos, speed, direction = Vector3()):
        self.model = model
        self.pos = pos
        self.speed = speed
        self.direction = direction
        self.discard = False
    
    def move(self, dt):
        self.pos.x += self.direction.x * self.speed * dt
        self.pos.y += self.direction.y * self.speed * dt
        self.pos.z += self.direction.z * self.speed * dt

    def update(self, dt):
        self.move(dt)

    def draw(self):
        draw_model(self.model, self.pos, 1, WHITE)

class Floor(Model):
    def __init__(self, texture):
        model = load_model_from_mesh(gen_mesh_cube(32,1,32))
        set_material_texture(model.materials[0], MATERIAL_MAP_ALBEDO, texture)
        super().__init__(model, Vector3(6.5,-2,-8), 0)

class Player(Model):
    def __init__(self, model, shoot_laser):
        super().__init__(model, Vector3(), PLAYER_SPEED)
        self.shoot_laser = shoot_laser
        self.angle = 0
        self.base_y = 0
        self.target_angle = 0  # Target angle for smooth rotation
        self.bob_offset = 0  # Offset for smooth bobbing
        
        # First rotate to face forward, then scale
        self.base_transform = matrix_multiply(
            matrix_rotate_y(90.0 * DEG2RAD),   # Face forward
            matrix_rotate_x(0.0 * DEG2RAD)     # Level
        )
        # Apply scaling after rotation
        self.base_transform = matrix_multiply(
            matrix_scale(0.005, 0.005, 0.005),
            self.base_transform
        )
        self.model.transform = self.base_transform
    
    def input(self):
        # Move left/right with arrow keys
        if is_key_down(KEY_RIGHT):
            self.direction.x = 1
            self.target_angle = -5  # Target tilt angle
        elif is_key_down(KEY_LEFT):
            self.direction.x = -1
            self.target_angle = 5   # Target tilt angle
        else:
            self.direction.x = 0
            self.target_angle = 0
            
        if is_key_pressed(KEY_SPACE):
            self.shoot_laser(Vector3Add(self.pos, Vector3(0,0,-1)))

    def update(self, dt):
        self.input()
        
        # Smooth horizontal movement with original bounds
        target_x = self.pos.x + self.direction.x * self.speed * dt
        self.pos.x = max(-4, min(target_x, 4))  # Restore original bounds
        
        # Smooth bobbing motion
        self.bob_offset += dt * 2  # Slower bobbing
        self.pos.y = self.base_y + sin(self.bob_offset) * 0.1
        
        # Smooth rotation
        angle_diff = self.target_angle - self.angle
        self.angle += angle_diff * dt * 5  # Smooth interpolation
        
        # Apply transforms
        if abs(self.angle) > 0.01:  # Only apply rotation if significant
            tilt = matrix_rotate_y(self.angle * DEG2RAD)
            self.model.transform = matrix_multiply(self.base_transform, tilt)
        else:
            self.model.transform = self.base_transform

    def draw(self):
        draw_model(self.model, self.pos, 1.0, WHITE)

class Laser(Model):
    def __init__(self, model, pos, texture):
        super().__init__(model, pos, LASER_SPEED, Vector3(0,0,-1))
        set_material_texture(self.model.materials[0], MATERIAL_MAP_ALBEDO, texture)

class Meteor(Model):
    def __init__(self, model):
        # setup
        pos = Vector3(uniform(-5, 5), 0, -20)  # Adjusted spawn range to match sleigh movement
        self.visual_radius = uniform(2.0, 2.5)  # Visual size for model
        self.radius = self.visual_radius * 0.4  # Smaller hit box (40% of visual size)
        # Use the coal model and scale it
        self.model = model
        self.model.transform = matrix_multiply(
            matrix_scale(self.visual_radius, self.visual_radius, self.visual_radius),
            matrix_rotate_y(uniform(0, 360) * DEG2RAD)  # Just random initial orientation
        )
        super().__init__(model, pos, uniform(*METEOR_SPEED_RANGE), Vector3(0,0,uniform(0.75,1.25)))

        # Very gentle, consistent rotation
        self.rotation = Vector3(0, 0, 0)
        self.rotation_speed = Vector3(0, 0.1, 0)  # Only rotate gently around Y axis

        # discard logic
        self.hit = False
        self.death_timer = Timer(0.25, False, False, self.activate_discard)
        self.death_timer.time = 0  # Reset timer
    
        # shader setup
        shader_path = os.path.join(GAME_ROOT, 'shaders', 'flash.fs')
        self.shader = load_shader(ffi.NULL, shader_path)
        self.material_count = self.model.materialCount
        # Apply shader to all materials in the model
        for i in range(self.material_count):
            self.model.materials[i].shader = self.shader
        self.flash_loc = get_shader_location(self.shader, 'flash')
        self.flash_value = 0.0
        self.flash_amount = ffi.new('float[2]', [0.0, 0.0])

    def flash(self):
        self.hit = True  # Mark as hit immediately
        self.flash_value = 0.6  # Reduced initial flash intensity for subtlety
        self.flash_amount[0] = self.flash_value
        # Apply flash to all materials immediately
        for i in range(self.material_count):
            set_shader_value(self.shader, self.flash_loc, self.flash_amount, SHADER_UNIFORM_VEC2)
        self.death_timer.active = True  # Activate death timer

    def activate_discard(self):
        self.discard = True

    def update(self, dt):
        self.death_timer.update()
        if not self.hit:
            super().update(dt)
            # Very gentle rotation
            self.rotation.y += self.rotation_speed.y * dt
            # Apply transform - cache the scale matrix
            scale_matrix = matrix_scale(self.visual_radius, self.visual_radius, self.visual_radius)
            self.model.transform = matrix_multiply(
                scale_matrix,
                matrix_rotate_y(self.rotation.y)  # Only Y rotation
            )
        # Update flash effect even when hit
        if self.flash_value > 0:
            self.flash_value = max(0.0, self.flash_value - dt * 2.5)  # Smoother fade
            self.flash_amount[0] = self.flash_value
            # Update shader only if flash is significant
            if self.flash_value > 0.005:  # Lower threshold for smoother fade-out
                for i in range(self.material_count):
                    set_shader_value(self.shader, self.flash_loc, self.flash_amount, SHADER_UNIFORM_VEC2)