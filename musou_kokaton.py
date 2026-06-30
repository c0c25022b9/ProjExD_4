import math
import os
import random
import sys
import time
import pygame as pg


WIDTH = 1100  # ゲームウィンドウの幅
HEIGHT = 650  # ゲームウィンドウの高さ
os.chdir(os.path.dirname(os.path.abspath(__file__)))


def check_bound(obj_rct: pg.Rect) -> tuple[bool, bool]:
    """
    オブジェクトが画面内or画面外を判定し，真理値タプルを返す関数
    引数：こうかとんや爆弾，ビームなどのRect
    戻り値：横方向，縦方向のはみ出し判定結果（画面内：True／画面外：False）
    """
    yoko, tate = True, True
    if obj_rct.left < 0 or WIDTH < obj_rct.right:
        yoko = False
    if obj_rct.top < 0 or HEIGHT < obj_rct.bottom:
        tate = False
    return yoko, tate


def calc_orientation(org: pg.Rect, dst: pg.Rect) -> tuple[float, float]:
    """
    orgから見て，dstがどこにあるかを計算し，方向ベクトルをタプルで返す
    引数1 org：爆弾SurfaceのRect
    引数2 dst：こうかとんSurfaceのRect
    戻り値：orgから見たdstの方向ベクトルを表すタプル
    """
    x_diff, y_diff = dst.centerx-org.centerx, dst.centery-org.centery
    norm = math.sqrt(x_diff**2+y_diff**2)
    return x_diff/norm, y_diff/norm


class Bird(pg.sprite.Sprite):
    """
    ゲームキャラクター（こうかとん）に関するクラス
    """
    delta = {  # 押下キーと移動量の辞書
        pg.K_UP: (0, -1),
        pg.K_DOWN: (0, +1),
        pg.K_LEFT: (-1, 0),
        pg.K_RIGHT: (+1, 0),
    }

    def __init__(self, num: int, xy: tuple[int, int]):
        """
        こうかとん画像Surfaceを生成する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 xy：こうかとん画像の位置座標タプル
        """
        super().__init__()
        img0 = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        img = pg.transform.flip(img0, True, False)  # デフォルトのこうかとん
        self.imgs = {
            (+1, 0): img,  # 右
            (+1, -1): pg.transform.rotozoom(img, 45, 0.9),  # 右上
            (0, -1): pg.transform.rotozoom(img, 90, 0.9),  # 上
            (-1, -1): pg.transform.rotozoom(img0, -45, 0.9),  # 左上
            (-1, 0): img0,  # 左
            (-1, +1): pg.transform.rotozoom(img0, 45, 0.9),  # 左下
            (0, +1): pg.transform.rotozoom(img, -90, 0.9),  # 下
            (+1, +1): pg.transform.rotozoom(img, -45, 0.9),  # 右下
        }
        self.dire = (+1, 0)
        self.image = self.imgs[self.dire]
        self.rect = self.image.get_rect()
        self.rect.center = xy
        self.speed = 10
        self.state = "normal"
        self.hyper_life = 0

    def change_img(self, num: int, screen: pg.Surface):
        """
        こうかとん画像を切り替え，画面に転送する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 screen：画面Surface
        """
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        screen.blit(self.image, self.rect)

    def update(self, key_lst: list[bool], screen: pg.Surface):
        """
        押下キーに応じてこうかとんを移動させる
        引数1 key_lst：押下キーの真理値リスト
        引数2 screen：画面Surface
        """
        sum_mv = [0, 0]
        for k, mv in __class__.delta.items():
            if key_lst[k]:
                sum_mv[0] += mv[0]
                sum_mv[1] += mv[1]
        self.rect.move_ip(self.speed*sum_mv[0], self.speed*sum_mv[1])
        if check_bound(self.rect) != (True, True):
            self.rect.move_ip(-self.speed*sum_mv[0], -self.speed*sum_mv[1])
        if not (sum_mv[0] == 0 and sum_mv[1] == 0):
            self.dire = tuple(sum_mv)
            self.image = self.imgs[self.dire]
        
        # 無敵状態（hyper）の処理（ラプラシアンフィルタで光らせる）
        if self.state == "hyper":
            self.hyper_life -= 1
            # 毎フレーム重ね掛けして画像がバグるのを防ぐため、元画像に対してフィルタをかける
            self.image = pg.transform.laplacian(self.imgs[self.dire])
            if self.hyper_life < 0:
                self.state = "normal"
                
        screen.blit(self.image, self.rect)


class Bomb(pg.sprite.Sprite):
    """
    爆弾に関するクラス
    """
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]

    def __init__(self, emy: "Enemy", bird: Bird):
        """
        爆弾円Surfaceを生成する
        引数1 emy：爆弾を投下する敵機
        引数2 bird：攻撃対象のこうかとん
        """
        super().__init__()
        rad = random.randint(10, 50)  # 爆弾円の半径：10以上50以下の乱数
        self.image = pg.Surface((2*rad, 2*rad))
        color = random.choice(__class__.colors)  # 爆弾円の色：クラス変数からランダム選択
        pg.draw.circle(self.image, color, (rad, rad), rad)
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()
        # 爆弾を投下するemyから見た攻撃対象のbirdの方向を計算
        self.vx, self.vy = calc_orientation(emy.rect, bird.rect)  
        self.rect.centerx = emy.rect.centerx
        self.rect.centery = emy.rect.centery+emy.rect.height//2
        self.speed = 6
        self.state = "active"  # 初期状態をアクティブに設定

    def update(self):
        """
        爆弾を速度ベクトルself.vx, self.vyに基づき移動させる
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class Beam(pg.sprite.Sprite):
    """
    ビームに関するクラス
    """
    def __init__(self, bird: Bird):
        """
        ビーム画像Surfaceを生成する
        引数 bird：ビームを放つこうかとん
        """
        super().__init__()
        self.vx, self.vy = bird.dire
        angle = math.degrees(math.atan2(-self.vy, self.vx))
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), angle, 1.0)
        self.vx = math.cos(math.radians(angle))
        self.vy = -math.sin(math.radians(angle))
        self.rect = self.image.get_rect()
        self.rect.centery = bird.rect.centery+bird.rect.height*self.vy
        self.rect.centerx = bird.rect.centerx+bird.rect.width*self.vx
        self.speed = 10

    def update(self):
        """
        ビームを速度ベクトルself.vx, self.vyに基づき移動させる
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class Explosion(pg.sprite.Sprite):
    """
    爆発に関するクラス
    """
    def __init__(self, obj: "Bomb|Enemy", life: int):
        """
        爆弾が爆発するエフェクトを生成する
        引数1 obj：爆発するBombまたは敵機インスタンス
        引数2 life：爆発時間
        """
        super().__init__()
        img = pg.image.load(f"fig/explosion.gif")
        self.imgs = [img, pg.transform.flip(img, 1, 1)]
        self.image = self.imgs[0]
        self.rect = self.image.get_rect(center=obj.rect.center)
        self.life = life

    def update(self):
        """
        爆発時間を1減算した爆発経過時間_lifeに応じて爆発画像を切り替えることで
        爆発エフェクトを表現する
        """
        self.life -= 1
        self.image = self.imgs[self.life//10%2]
        if self.life < 0:
            self.kill()


class Enemy(pg.sprite.Sprite):
    """
    敵機に関するクラス
    """
    imgs = [pg.image.load(f"fig/alien{i}.png") for i in range(1, 4)]
    
    def __init__(self):
        super().__init__()
        self.image = pg.transform.rotozoom(random.choice(__class__.imgs), 0, 0.8)
        self.rect = self.image.get_rect()
        self.rect.center = random.randint(0, WIDTH), 0
        self.vx, self.vy = 0, +6
        self.bound = random.randint(50, HEIGHT//2)  # 停止位置
        self.state = "down"  # 降下状態or停止状態
        self.interval = random.randint(50, 300)  # 爆弾投下インターバル

    def update(self):
        """
        敵機を速度ベクトルself.vyに基づき移動（降下）させる
        ランダムに決めた停止位置_boundまで降下したら，_stateを停止状態に変更する
        """
        if self.rect.centery > self.bound:
            self.vy = 0
            self.state = "stop"
        self.rect.move_ip(self.vx, self.vy)


class Score:
    """
    打ち落とした爆弾，敵機の数をスコアとして表示するクラス
    爆弾：1点
    敵機：10点
    """
    def __init__(self):
        self.font = pg.font.Font(None, 50)
        self.color = (0, 0, 255)
        self.value = 0
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        self.rect = self.image.get_rect()
        self.rect.center = 100, HEIGHT-50

    def update(self, screen: pg.Surface):
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        screen.blit(self.image, self.rect)


class Gravity(pg.sprite.Sprite):
    """
    追加機能１：こうかとんの残機数（ライフ）を表示・管理するクラス
    """
    def __init__(self, life: int):
        super().__init__()
        self.image = pg.Surface((WIDTH, HEIGHT))
        pg.draw.rect(self.image, (0, 0, 0), (0, 0, WIDTH, HEIGHT))
        self.image.set_alpha(128)
        self.rect = self.image.get_rect()
        self.life = life

    def update(self, screen: pg.Surface):
        # 残機数（self.num）の分だけハートを並べて描画する
        for i in range(self.num):
            # 最右ハートの重心（中心）が下から50，右から50の位置
            # 40x40のSurfaceの中心を(WIDTH-50, HEIGHT-50)にするため、左上座標は(WIDTH-70, HEIGHT-70)
            # i番目のハートは左に並べるため、x座標から i * 40 を引く
            x = (WIDTH - 70) - i * 40
            y = HEIGHT - 70
            screen.blit(self.image, (x, y))


class Emp(pg.sprite.Sprite):
    """
    発動時に存在する敵機と爆弾を無効化する
    """
    def __init__(self, emys: pg.sprite.Group, bombs: pg.sprite.Group, screen: pg.Surface):
        super().__init__()
        self.image = pg.Surface((WIDTH, HEIGHT))
        pg.draw.rect(self.image, (255, 255, 0), (0, 0, WIDTH, HEIGHT))
        self.image.set_alpha(100)
        self.rect = self.image.get_rect()
        self.life = 3

        for emy in emys:  # 敵機の無効化
            emy.interval = float("inf")
            
            filter_img = emy.image.copy()
            pxarray = pg.PixelArray(filter_img)
            colorkey = emy.image.get_colorkey()
            for x in range(filter_img.get_width()):
                for y in range(filter_img.get_height()):
                    raw_color = emy.image.get_at((x, y))
                    if raw_color.a == 0 or (colorkey and raw_color[:3] == colorkey[:3]):
                        continue
                    
                    r = 255 - raw_color.r
                    g = 255 - raw_color.g
                    b = 255 - raw_color.b
                    pxarray[x, y] = (r, g, b)
            
            del pxarray
            emy.image = filter_img

        for bomb in bombs:  # 爆弾の無効化
            bomb.speed /= 2
            bomb.state = "inactive"

    def update(self):
        self.life -= 1
        if self.life < 0:
            self.kill()


class Life:
    """
    追加機能１：こうかとんの残機数（ライフ）を表示・管理するクラス
    """
    def __init__(self, num: int):
        self.num = num
        self.image = pg.Surface((40, 40))
        self.image.set_colorkey((0, 0, 0))  # 黒色部分を透明化
        # ハートの形
        points = [
            (16 * math.sin(t / 100) ** 3 + 20, 
             -(13 * math.cos(t / 100) - 5 * math.cos(2 * t / 100) - 2 * math.cos(3 * t / 100) - math.cos(4 * t / 100)) + 20) 
            for t in range(0, 628)
        ]
        pg.draw.polygon(self.image, (255, 0, 0), points)  # 空のSurfaceに赤色のハートをdraw

    def update(self, screen: pg.Surface):
        # 残機数（self.num）の分だけハートを並べて描画する
        for i in range(self.num):
            x = (WIDTH - 70) - i * 40
            y = HEIGHT - 70
            screen.blit(self.image, (x, y))


def main():
    pg.display.set_caption("真！こうかとん無双")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    bg_img = pg.image.load(f"fig/pg_bg.jpg")
    score = Score()
    life = Life(3)  # ライフを初期値3で生成

    life = Life(3)

    bird = Bird(3, (900, 400))
    bombs = pg.sprite.Group()
    beams = pg.sprite.Group()
    exps = pg.sprite.Group()
    emys = pg.sprite.Group()
    gravities = pg.sprite.Group()
    emps = pg.sprite.Group()

    tmr = 0
    clock = pg.time.Clock()
    while True:
        key_lst = pg.key.get_pressed()
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return 0
            if event.type == pg.KEYDOWN:
                # スペースキー：ビーム発動
                if event.key == pg.K_SPACE:
                    beams.add(Beam(bird))
                
                # リターンキー：重力場発動（条件：スコア > 200, 消費スコア：200, 400フレーム持続）
                if event.key == pg.K_RETURN and score.value > 200:
                    score.value -= 200
                    gravities.add(Gravity(400))
                
                # eキー：EMP発動（条件：スコア >= 20, 消費スコア：20）
                if event.key == pg.K_e and score.value >= 20:
                    score.value -= 20
                    emps.add(Emp(emys, bombs, screen))

                # 【追加機能４】右Shiftキー：無敵状態発動（条件：スコア > 100, 消費スコア：100, 500フレーム持続）
                if event.key == pg.K_RSHIFT and score.value > 100:
                    score.value -= 100
                    bird.state = "hyper"
                    bird.hyper_life = 500

        screen.blit(bg_img, [0, 0])

        if tmr%200 == 0:  # 200フレームに1回，敵機を出現させる
            emys.add(Enemy())

        for emy in emys:
            if emy.state == "stop" and tmr%emy.interval == 0:
                bombs.add(Bomb(emy, bird))

        for emy in pg.sprite.groupcollide(emys, beams, True, True).keys():  # ビームと衝突した敵機
            exps.add(Explosion(emy, 100))
            score.value += 10
            bird.change_img(6, screen)

        for bomb in pg.sprite.groupcollide(bombs, beams, True, True).keys():  # ビームと衝突した爆弾
            exps.add(Explosion(bomb, 50))
            score.value += 1

        # 重力場と敵機・爆弾の衝突処理
        for emy in pg.sprite.groupcollide(emys, gravities, True, False).keys():
            exps.add(Explosion(emy, 100))
            
        for bomb in pg.sprite.groupcollide(bombs, gravities, True, False).keys():
            exps.add(Explosion(bomb, 50))

        # こうかとんと爆弾の衝突判定
        hit_bombs = pg.sprite.spritecollide(bird, bombs, True)
        for bomb in hit_bombs:
            if bomb.state == "inactive":
                continue  # EMPにより無効化された爆弾ならダメージを受けない
            
            if bird.state == "hyper":
                # 無敵状態なら爆弾を相殺してスコア加算
                exps.add(Explosion(bomb, 50))
                score.value += 1
            else:
                # 通常状態で被弾した場合、ライフを1減らす
                life.num -= 1
                exps.add(Explosion(bomb, 50))
                
                if life.num <= 0:
                    # ライフが0になったらゲームオーバー処理
                    bird.change_img(8, screen)  # こうかとん悲しみエフェクト
                    score.update(screen)
                    life.update(screen)
                    pg.display.update()
                    time.sleep(2)
                    return
                else:
                    # ライフが残っているなら、一定時間無敵状態（hyper）にする（被弾時：100フレーム無敵）
                    bird.state = "hyper"
                    bird.hyper_life = 100

        bird.update(key_lst, screen)
        beams.update()
        beams.draw(screen)
        emys.update()
        emys.draw(screen)
        bombs.update()
        bombs.draw(screen)
        exps.update()
        exps.draw(screen)
        emps.update()
        emps.draw(screen)
        score.update(screen)
        life.update(screen)  # ライフ（ハート）の描画更新
        
        pg.display.update()
        tmr += 1
        clock.tick(50)


if __name__ == "__main__":
    pg.init()
    main()
    pg.quit()
    sys.exit()