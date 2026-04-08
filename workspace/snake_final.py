import pygame
import random
import time

def run_game():
    pygame.init()
    width, height = 600, 400
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption("Archimedes Snake Demo")
    
    blue = (50, 153, 213)
    black = (0, 0, 0)
    red = (213, 50, 80)
    green = (0, 255, 0)
    
    snake_block = 20
    snake_speed = 10
    
    x1, y1 = width / 2, height / 2
    x1_change, y1_change = 0, 0
    
    snake_list = []
    length_of_snake = 1
    
    foodx = round(random.randrange(0, width - snake_block) / 20.0) * 20.0
    foody = round(random.randrange(0, height - snake_block) / 20.0) * 20.0
    
    clock = pygame.time.Clock()
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    x1_change = -snake_block
                    y1_change = 0
                elif event.key == pygame.K_RIGHT:
                    x1_change = snake_block
                    y1_change = 0
                elif event.key == pygame.K_UP:
                    y1_change = -snake_block
                    x1_change = 0
                elif event.key == pygame.K_DOWN:
                    y1_change = snake_block
                    x1_change = 0
                    
        x1 += x1_change
        y1 += y1_change
        
        if x1 >= width or x1 < 0 or y1 >= height or y1 < 0:
            running = False
            
        screen.fill(blue)
        pygame.draw.rect(screen, red, [foodx, foody, snake_block, snake_block])
        
        snake_head = [x1, y1]
        snake_list.append(snake_head)
        if len(snake_list) > length_of_snake:
            del snake_list[0]
            
        for x in snake_list:
            pygame.draw.rect(screen, black, [x[0], x[1], snake_block, snake_block])
            
        pygame.display.update()
        
        if x1 == foodx and y1 == foody:
            foodx = round(random.randrange(0, width - snake_block) / 20.0) * 20.0
            foody = round(random.randrange(0, height - snake_block) / 20.0) * 20.0
            length_of_snake += 1
            
        clock.tick(snake_speed)
        
    pygame.quit()

if __name__ == "__main__":
    run_game()
