from settings import * 
from models import Floor, Player, Laser, Meteor
import os

# Get the absolute path to the game root directory
GAME_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

METEOR_TIMER_DURATION = 1.5  # Slower spawn rate
MAX_METEORS = 8  # Limit maximum meteors

class Game:
    def __init__(self):
        init_window(WINDOW_WIDTH, WINDOW_HEIGHT, "Space shooter")
        set_target_fps(60)  # Lock to 60 FPS for smooth performance
        init_audio_device()
        self.import_assets()
        self.game_state = "start"  # start, playing, game_over
        self.reset_game()
        
    def create_meteor(self):
        if len(self.meteors) < MAX_METEORS:  # Only spawn if under limit
            self.spawn_meteor()

    def shoot_laser(self, pos):
        self.lasers.append(Laser(self.models['laser'], pos, self.light_texture))
        play_sound(self.audio['laser'])

    def import_assets(self):
        self.models = {
            'player': load_model(os.path.join(GAME_ROOT, 'models', 'santasleigh.glb')),
            'laser': load_model(os.path.join(GAME_ROOT, 'models', 'laser.glb')),
            'coal': load_model(os.path.join(GAME_ROOT, 'models', 'coal.glb'))
        }

        self.audio = {
            'laser': load_sound(os.path.join(GAME_ROOT, 'audio', 'laser.wav')),
            'explosion': load_sound(os.path.join(GAME_ROOT, 'audio', 'explosion.wav')),
            'music': load_music_stream(os.path.join(GAME_ROOT, 'audio', 'music.wav')),
        }

        self.textures = [load_texture(os.path.join(GAME_ROOT, 'textures', f'{color}.png')) for color in ('red', 'green', 'orange', 'purple')]
        self.dark_texture = load_texture(os.path.join(GAME_ROOT, 'textures', 'dark.png'))
        self.light_texture = load_texture(os.path.join(GAME_ROOT, 'textures', 'light.png'))
        
        # Load background texture
        self.background = load_texture(os.path.join(GAME_ROOT, 'textures', 'background.png'))
        
        self.font = load_font_ex(os.path.join(GAME_ROOT, 'font', 'Stormfaze.otf'), FONT_SIZE, ffi.NULL, 0)
 
    def reset_game(self):
        # game state
        self.close = False
        self.score = 0
        self.last_update = get_time()  # Track last update time

        # camera - restore original perspective
        self.camera = Camera3D()
        self.camera.position = Vector3(-4.0, 8.0, 6.0)
        self.camera.target = Vector3(0.0, 0.0, -1.0)
        self.camera.up = Vector3(0.0, 1.0, 0.0)
        self.camera.fovy = 45.0
        self.camera.projection = CAMERA_PERSPECTIVE

        # create player
        self.player = Player(self.models['player'], self.shoot_laser)
        
        # create object pools
        self.lasers = []
        self.meteors = []
        self.meteor_timer = Timer(METEOR_TIMER_DURATION, True, True, self.create_meteor)
        
    def spawn_meteor(self):
        self.meteors.append(Meteor(self.models['coal']))

    def check_discard(self):
        self.lasers = [laser for laser in self.lasers if not laser.discard]
        self.meteors = [meteor for meteor in self.meteors if not meteor.discard]

    def check_collisions(self):
        if self.game_state != "playing":
            return

        # player -> meteor
        for meteor in self.meteors:
            if check_collision_spheres(self.player.pos, 0.8, meteor.pos, meteor.radius):
                self.game_state = "game_over"
                play_sound(self.audio['explosion'])
                return

        # laser -> meteor
        for laser in self.lasers:
            for meteor in self.meteors:
                laser_bbox = get_mesh_bounding_box(laser.model.meshes[0])
                col_bbox = BoundingBox(
                    Vector3Add(laser_bbox.min, laser.pos), # min
                    Vector3Add(laser_bbox.max, laser.pos), # max
                )
                if check_collision_box_sphere(col_bbox, meteor.pos, meteor.radius):
                    meteor.hit = True
                    laser.discard = True
                    meteor.death_timer.activate()
                    meteor.flash()
                    play_sound(self.audio['explosion'])
                    self.score += 1

    def update(self):
        if self.game_state == "start":
            if is_key_pressed(KEY_SPACE):
                self.game_state = "playing"
                play_music_stream(self.audio['music'])
        elif self.game_state == "playing":
            # Calculate delta time
            current_time = get_time()
            dt = current_time - self.last_update
            self.last_update = current_time
            
            # Update game logic with consistent delta time
            self.meteor_timer.update()
            self.check_discard()
            self.check_collisions()
            
            # Update all game objects
            for laser in self.lasers:
                laser.update(dt)
            for meteor in self.meteors:
                meteor.update(dt)
            self.player.update(dt)
            
            # Clean up meteors that are too far
            self.meteors = [m for m in self.meteors if m.pos.z < 10]
            
            # Update music stream
            update_music_stream(self.audio['music'])
            
        # Handle game over state
        if self.game_state == "game_over":
            if is_key_pressed(KEY_R):
                self.game_state = "playing"
                self.reset_game()
            elif is_key_pressed(KEY_ESCAPE):
                self.close = True
                
    def draw_shadows(self):
        # Player shadow
        if not self.player.discard:
            player_radius = max(0.1, 0.5 + self.player.pos.y)
            draw_cylinder(
                Vector3(self.player.pos.x, -1.5, self.player.pos.z),
                player_radius,
                player_radius,
                0.1,
                20,
                Color(0, 0, 0, 50)
            )

        # Meteor shadows
        for meteor in self.meteors:
            if not meteor.discard and meteor.radius > 0:
                shadow_radius = max(0.1, meteor.radius * 0.8)
                draw_cylinder(
                    Vector3(meteor.pos.x, -1.5, meteor.pos.z),
                    shadow_radius,
                    shadow_radius,
                    0.1,
                    20,
                    Color(0, 0, 0, 50)
                )

    def draw_score(self):
        score = str(int(get_time()))
        draw_text_ex(self.font, score, Vector2(WINDOW_WIDTH - FONT_PADDING, WINDOW_HEIGHT - FONT_PADDING), FONT_SIZE, 2, WHITE)
        
    def draw(self):
        begin_drawing()
        clear_background(BLACK)
        
        # Draw background texture
        draw_texture_ex(
            self.background,
            Vector2(0, 0),
            0.0,  # rotation
            float(WINDOW_WIDTH) / float(self.background.width),  # scale to window width
            WHITE
        )
        
        if self.game_state == "start":
            # Draw start screen with background
            title_text = "SANTA'S COAL CRUSHER"
            subtitle_text = "Press SPACE to Start"
            controls_text = [
                "Controls:",
                "LEFT/RIGHT - Move Santa",
                "SPACE - Shoot Laser",
                "ESC - Quit"
            ]
            
            # Calculate total content height
            title_height = 60
            subtitle_height = 30
            controls_height = len(controls_text) * 30
            spacing = 40  # Space between sections
            total_height = title_height + spacing + subtitle_height + spacing + controls_height
            
            # Calculate starting Y position to center everything vertically
            start_y = (WINDOW_HEIGHT - total_height) // 2
            
            # Draw title (centered)
            title_size = measure_text(title_text, 60)
            draw_text(title_text, (WINDOW_WIDTH - title_size) // 2, start_y, 60, WHITE)
            
            # Draw subtitle (centered)
            subtitle_y = start_y + title_height + spacing
            subtitle_size = measure_text(subtitle_text, 30)
            draw_text(subtitle_text, (WINDOW_WIDTH - subtitle_size) // 2, subtitle_y, 30, WHITE)
            
            # Draw controls (centered)
            controls_y = subtitle_y + subtitle_height + spacing
            for i, text in enumerate(controls_text):
                text_size = measure_text(text, 30)  # Increased control text size
                draw_text(text, (WINDOW_WIDTH - text_size) // 2, controls_y + i * 35, 30, WHITE)
                
        else:
            begin_mode_3d(self.camera)
            
            # Draw all 3D models
            self.player.draw()
            
            # Draw meteors
            for meteor in self.meteors:
                meteor.draw()
                
            # Draw lasers
            for laser in self.lasers:
                laser.draw()
            
            end_mode_3d()
            
            # Draw score with shadow for better visibility
            score_text = f"Score: {self.score}"
            draw_text(score_text, 42, 32, 40, BLACK)  # Shadow
            draw_text(score_text, 40, 30, 40, WHITE)  # Main text
            
            if self.game_state == "game_over":
                game_over_text = "Game Over!"
                restart_text = "Press R to restart or ESC to quit"
                
                # Draw game over text
                text_size = measure_text(game_over_text, 60)
                draw_text(game_over_text, (WINDOW_WIDTH - text_size) // 2, 200, 60, WHITE)
                
                # Draw restart instructions
                restart_size = measure_text(restart_text, 30)
                draw_text(restart_text, (WINDOW_WIDTH - restart_size) // 2, 300, 30, WHITE)
        
        end_drawing()

    def unload(self):
        # Unload textures
        unload_texture(self.background)
        
        # Unload models
        for model in self.models.values():
            unload_model(model)
        
        # Unload sounds - handle Sound and Music separately
        unload_sound(self.audio['laser'])
        unload_sound(self.audio['explosion'])
        unload_music_stream(self.audio['music'])
        
        close_window()

    def run(self):
        while not window_should_close() and not self.close:
            self.update()
            self.draw()
            
        unload_music_stream(self.audio['music'])
        close_audio_device()
        self.unload()

if __name__ == '__main__':
    game = Game()
    game.run()