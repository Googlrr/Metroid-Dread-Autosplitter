import cv2
import time
import numpy                    as np 
from time                       import sleep
from PIL                        import Image
from auto_splitter.capture      import Capture
from auto_splitter.coordinates  import Coordinates
from auto_splitter.route        import Route
from auto_splitter.livesplit    import LivesplitServer
import auto_splitter.variables  as variables
#import PySimpleGUI              as sg

class AutoSplitter():

    def __init__(self, x,y,w,h,c,window,route,livesplit_server, livesplit_port, load_remover_only=False):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.c = c
        self.watching = False
        self.scale = w/1920
        self.trigger_distance = 10
        self.window = window
        self.route = route
        self.livesplit_server = livesplit_server
        self.livesplit_port = livesplit_port
        self.load_remover_only = load_remover_only

    def array_distance(self, arr1, arr2, num):
        if (arr1[0] < arr2[0] + num) and (arr1[0] > arr2[0] - num) and (arr1[1] < arr2[1] + num) and (arr1[1] > arr2[1] - num) and (arr1[2] < arr2[2] + num) and (arr1[2] > arr2[2] - num):
                return True
        else: 
            return False

    def lessthan(self, arr, num): 
        if arr[0] < num and arr[1] < num and arr[2] < num: 
            return True
        else: 
            return False

    def average_colors(self, frame, args):
        total = [0,0,0]        
        for arg in args:
            arg_color = Capture.get_average_color_from_frame(frame, arg)
            total[0] += arg_color[0]
            total[1] += arg_color[1]
            total[2] += arg_color[2]
        return [int(total[0]/len(args)),int(total[1]/len(args)),int(total[2]/len(args))]

    def stop_watcher(self): 
        self.watching = False
        print('Set stop flag...')
    
    #def update_window(self, window, text): 

    def start_watcher(self):
        self.watching = True

        update_window = lambda x, y: self.window[x].update(y) if self.watching else False

        get_items_in_text = lambda x, y: [i for i in x if i in y]
        get_uppercase_items = lambda x: [i.upper() for i in x]

        x, y, w, h, c = self.x, self.y, self.w, self.h, self.c

        scale = w/1920
        item_coords, location_coords, menu_coords = variables.get_coordinates(x,y,w/1920)
        item_triggers = [
            Coordinates(420, 420, 620, 650, x, y, scale),
            Coordinates(1290, 420, 1490, 650, x, y, scale)
        ]

        item_trigger_value = [2, 12, 23]

        menu_triggers = [
            Coordinates(392, 462, 1533, 507, x, y, scale),
            Coordinates(392, 605, 1533, 650, x, y, scale),
            Coordinates(392, 749, 1533, 794, x, y, scale)
        ]

        menu_trigger_values = [[160, 46, 64], 
                               [31, 48, 56], 
                               [25, 41, 48]
        ]

        escape_sequence_trigger_value = [36, 1, 7]

        locations, upgrades, items = variables.locations, variables.upgrades, variables.item_types
        
        whole_screen_trigger = Coordinates(0, 0, 1920, 1080, x, y, scale)

        location_triggers = [
            Coordinates(50,50,550,250,x,y,scale),
            Coordinates(1370,50,1870,250,x,y,scale)
        ]

        loading_symbol = Coordinates(1750, 920, 1780, 950, x, y, scale)
        loading_symbol_trigger = [201, 255, 254]

        location_trigger_value = [0, 1, 8]

        last_time = time.time()

        cap = Capture(c, 1920, 1080)

        running = False
        
        ls = LivesplitServer(self.livesplit_server, self.livesplit_port, self.load_remover_only)
        ls.connect()

        route = Route(self.route) if not self.load_remover_only else Route([])
        current_location = locations[0]

        item_cooldown = 0
        upgrade_cooldown = 0
        item_count = 0
        split_location_before, split_location_after = 0, 0

        game_time_status = False
        timer_stage = 0

        death_screen_trigger = [39, 33, 43]

        end_frame_trigger = [55, 97, 127] #[55, 97, 127]
        end_frame_loc_trigger = [93, 165, 200] #[93, 165, 200]

        self.window['-STAT1-'].update('Current Location: %s' % "Artaria", text_color='green')
        self.window['-STAT2-'].update('Items Collected: %s' % item_count, text_color='green')
        self.window['-STAT3-'].update('Next Split: %s' % route.print_current_split())

        if self.load_remover_only:
            print("Starting in load remover only mode. Will not split! Will still start/stop GAME TIME in Livesplit.")

        print("Note: Game time in the first 10 seconds may appear wrong. It will reset before the initial load finishes!")
        watch_for_end_frame = False

        ls_index_sync_time = 0

        while self.watching:
            ret, frame = cap.read()

            if ret:
                avg = cap.get_average_color_from_frame(frame, whole_screen_trigger)

                if not running: 
                    averages = [
                        cap.get_average_color_from_frame(frame, menu_triggers[0]),
                        cap.get_average_color_from_frame(frame, menu_triggers[1]),
                        cap.get_average_color_from_frame(frame, menu_triggers[2])
                    ]
                    if self.array_distance(averages[1], menu_trigger_values[1], self.trigger_distance) and self.array_distance(averages[2], menu_trigger_values[2], self.trigger_distance):
                        update_window('-STAT4-', 'Detecting: File menu')
                        if averages[0][0] > menu_trigger_values[0][0] + 15:
                            print("Detected file start! Starting RTA timer...")
                            update_window('-STAT4-', 'Starting run...')
                            ls.start_timer()
                            running = True
                            game_time_status = False
                            timer_stage = 4
                            sleep(10)
                            ls.stop_game_timer()
                            ls.reset_game_time()
                            ret, frame = cap.read()
                    else:
                        update_window('-STAT4-', 'Detecting: ???')
                        #self.window['-STAT4-'].update('Detecting: ???')

                else: 
                    screen_color = cap.get_average_color_from_frame(frame, whole_screen_trigger)

                    if self.lessthan(screen_color, 10):
                        update_window('-STAT4-', 'Detecting: Black Screen')
                        if timer_stage == 0:
                            loading_colors = cap.get_average_color_from_frame(frame, loading_symbol)
                            if self.array_distance(loading_colors, loading_symbol_trigger, 4):
                                timer_stage = 6
                        if timer_stage == 1: 
                            ls.stop_game_timer()
                            game_time_status = False
                            timer_stage = 2
                        elif timer_stage == 3: 
                            timer_stage = 4
                        elif timer_stage == 6:
                            ls.stop_game_timer()
                            game_time_status = False
                            timer_stage = 4
                    elif watch_for_end_frame and self.array_distance(screen_color, end_frame_trigger, 10):
                        end_frame_2 = cap.get_average_color_from_frame(frame, location_coords)
                        print(end_frame_2)
                        if self.array_distance(end_frame_2, end_frame_loc_trigger, 10):
                            print("Is this the end?")
                            ls.send_split()
                            self.stop_watcher()

                    else: 
                        current_split = route.get_current_split()
                        loc_colors = self.average_colors(frame, location_triggers)
                        item_colors = self.average_colors(frame, item_triggers)

                        ## Timer pause/unpause stages
                        if timer_stage == 2: 
                            timer_stage = 3
                        elif timer_stage == 4:
                            ls.start_game_timer()
                            game_time_status = True
                            timer_stage = 0
                        
                        ## Watch for location trigger
                        if self.array_distance(loc_colors, location_trigger_value, self.trigger_distance) and timer_stage == 0:
                            update_window('-STAT4-', 'Detecting: Map Screen')
                            location_ocr = cap.get_text_from_frame(frame, location_coords, 40)
                            current_split = route.get_current_split()
                            not_current = lambda x, y: [i for i in y if i.upper() != x.upper()]
                            for loc in not_current(current_location, get_items_in_text(get_uppercase_items(locations), location_ocr)):

                                ##If current split is a Location change
                                if current_split[0] == "l":
                                    split_location_before   = current_split[1]
                                    split_location_after    = current_split[2]

                                    if current_location.lower() == locations[split_location_before].lower() and loc.lower() == locations[split_location_after].lower():
                                        print("%s to %s split found at %s" % (locations[split_location_before], locations[split_location_after], ls.get_current_time()))
                                        ls.send_split()
                                        route.progress_route()
                                        update_window('-STAT3-', 'Next Split: %s' % route.print_current_split())

                                print("Transporting from %s to %s at %s" % (current_location, loc, ls.get_current_time()))
                                timer_stage = 1
                                current_location = loc
                                update_window('-STAT1-', 'Current Location: %s' % loc)

                                if self.load_remover_only and loc == "Itorash":
                                    watch_for_end_frame = True

                        ## Watch for Death screen
                        elif self.array_distance(loc_colors, death_screen_trigger, 4) and timer_stage == 0 and "CONTINUE" in cap.get_text_from_frame(frame, item_coords, 80):
                            timer_stage = 6

                        ## Watch for the Item/Upgrade window
                        elif self.array_distance(item_colors, item_trigger_value, self.trigger_distance) and timer_stage == 0:
                            update_window('-STAT4-', 'Detecting: Upgrade/Item Window')
                            upgrade_ocr = cap.get_text_from_frame(frame, item_coords, 100)
                            if current_split[0] == "u" and upgrades[current_split[1]] in upgrade_ocr:
                                upg = upgrades[current_split[1]]
                                print("%s split found at %s" % (upg, ls.get_current_time()))
                                ls.send_split()
                                route.progress_route()
                                update_window('-STAT3-', 'Next Split: %s' % route.print_current_split())
                                upgrade_cooldown = 10

                            elif item_cooldown <= 0 or upgrade_cooldown <= 0:
                                if item_cooldown <= 0:
                                    for item in get_items_in_text(items, upgrade_ocr):
                                        print("Collected %s in %s at %s" % (item, current_location, ls.get_current_time()))
                                        item_cooldown = 10
                                        item_count += 1
                                        update_window('-STAT2-', 'Items Collected: %s' % item_count)

                                if upgrade_cooldown <= 0:
                                    for upg in get_items_in_text(upgrades, upgrade_ocr):
                                        print("Found %s at %s" % (upg, ls.get_current_time()))
                                        upgrade_cooldown = 10

                        ## No other watch conditions are active                        
                        else: 
                            update_window('-STAT4-', 'Game playing...')
                            
                        update_window('-STAT6-', 'Route Complete: %s, Timer_stage: %s' % (route.is_complete(), timer_stage))

                        #TIMEKEEPING LOGIC BELOW
                        end_time = time.time()
                        diff =  (end_time - last_time)

                        #Sync with Livesplit index every 10 seconds
                        if not self.load_remover_only:
                            ls_index_sync_time += diff
                            if ls_index_sync_time > 10: 
                                ls_index = ls.get_current_index()
                                if ls_index != route.route_pos:
                                    print("Skipping to split %s" % route.get_split_text(ls_index))
                                    route.set_route_position(ls_index)
                                ls_index_sync_time = 0

                        #Once an item/upgrade is collected, don't check for 10 more seconds
                        #Prevents duplicate readings....
                        if item_cooldown > 0:
                            item_cooldown -=  diff
                        if upgrade_cooldown > 0:
                            upgrade_cooldown -= diff

                        update_window('-STAT5-','Processing %s FPS' % round(1 / diff))
                        last_time = end_time

        print("Stopping thread?")