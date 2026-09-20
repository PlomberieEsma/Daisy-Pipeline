#                           .=     ,        =.
#                   _  _   /'/    )\,/,/(_   \ \
#                    `//-.|  (  ,\\)\//\)\/_  ) |
#                    //___\   `\\\/\\/\/\\///'  /
#                 ,-"~`-._ `"--'_   `"'"`  _ \`'"~-,_
#                 \       `-.  '_`.      .'_` \ ,-"~`/
#                  `.__.-'`/  ( -\        /- )|-.__,'
#                    ||   |    \ O)  /^\ (O / |
#                    `\\  |         /   `\    /
#                      \\  \       /      `\ /
#                       `\\ `-.  /' .---.--.\
#                         `\\/`~(, '()      ('
#                          /(O) \\   _,.-.,_)
#                         //  \\ `\'`      /
#                        / |  ||   `""'"~"`
#                      /'  |__||
#                            `o
#      ___       _                    _          ___               
#     / _ \___ _(_)__ __ __     ___  (_)__  ___ / (_)__  ___       
#    / // / _ `/ (_-</ // /    / _ \/ / _ \/ -_) / / _ \/ -_)      
#   /____/\_,_/_/___/\_, /    / .__/_/ .__/\__/_/_/_//_/\__/       
#                   /___/    /_/    /_/                            
#
#   by Noa Escourbanies, Leeloo Trinh-Thieu and Thomas Rubio
#   art by Joan G. Stark (Spunk)

import sys
import asyncio


def print_title():
    final1 = r"""
                        .=     ,        =.
                _  _   /'/    )\,/,/(_   \ \
                 `//-.|  (  ,\\)\//\)\/_  ) |
                 //___\   `\\\/\\/\/\\///'  /
              ,-"~`-._ `"--'_   `"'"`  _ \`'"~-,_
              \       `-.  '_`.      .'_` \ ,-"~`/
               `.__.-'`/  ( -\        /- )|-.__,'
                 ||   |    \ O)  /^\ (O / |
                 `\\  |         /   `\    /
                   \\  \       /      `\ /
                    `\\ `-.  /' .---.--.\
                      `\\/`~(, '()      ('
                       /(O) \\   _,.-.,_)
                      //  \\ `\'`      /
                     / |  ||   `""'"~"`
                   /'  |__||
                         `o
   ___       _                    _          ___               
  / _ \___ _(_)__ __ __     ___  (_)__  ___ / (_)__  ___       
 / // / _ `/ (_-</ // /    / _ \/ / _ \/ -_) / / _ \/ -_)      
/____/\_,_/_/___/\_, /    / .__/_/ .__/\__/_/_/_//_/\__/       
                /___/    /_/    /_/                            
"""
    print(final1 + "\n\nby Noa Escourbanies, Leeloo Trinh-Thieu and Thomas Rubio\nart by Joan G. Stark (Spunk)\n\n")

async def waiting_message(message="Please wait", timer=10):

    animation = ["/","—","\\","|"]
    anim_speed = 0.5

    i = 0
    print("\n\n\n")
    # await asyncio.sleep(1)
    while timer >= 0:
        if i < len(animation):
            print(message + " " + animation[i])
            sys.stdout.write("\033[F") # Cursor up one line

            i += 1
            # time.sleep(anim_speed)
            await asyncio.sleep(anim_speed)
            timer -= anim_speed
        else:
            i = 0