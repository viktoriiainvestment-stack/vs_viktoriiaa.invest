"""One-off seed of the leads currently live in the Liika artifact.

Run manually: `python seed.py`. Safe to re-run -- skips seeding if the
leads table already has rows, so it never duplicates data.
"""
import db

LEADS = [
    dict(name='Ігор Турцевич', phone='+380 (67) 656-51-11', stage='investor', portrait='Білорусь - Київ - досвід', diagnosis='ОФФЕР', offer='ArcHotel', decision='Угода (очікується)', notes='ArcHotel 05.2026 · ArcHotel 18.08', sortOrder=1),
    dict(name='Віктор Яблуниця', phone='0 (67) 570-23-56', stage='qualified', prevContact='16 серпня буде в Укр', sortOrder=2),
    dict(name='Андрій', phone='+380 (50) 471-53-15', stage='qualified', portrait='Варна цікавить тільки за кордон - скинути', diagnosis='Передача ліда', offer='Arcanum', notes='24.06 - дзвінок, скидаю на вайбер ВАРНУ, дітей каже краз туди везе', sortOrder=3),
    dict(name='Вікторія', phone='+380 (93) 712-92-71', stage='qualified', portrait='24.06 - скинути варну, дуже цікавить Болгарія а не Одеса в межах 50 тисяч', diagnosis='Передача ліда', offer='Arcanum', sortOrder=4),
    dict(name='Наталя', phone='+380 (97) 471-85-29', stage='qualified', portrait='Львів - вайбер - покупка на осінь +- - і капіталізація і пасив - закордон не цікаво, Київ страшно', diagnosis='ОФФЕР', offer='MOVIN', sortOrder=5),
    dict(name='Ігор Ама', phone='+380 (50) 330-87-40', stage='qualified', portrait='Пасив - від 100 - Київ - досвід жк Київ Одеса', diagnosis='заперечення', offer='MIY', sortOrder=6),
    dict(name='Роман', phone='+380 (97) 486-41-35', stage='qualified', prevContact='пон. 17:00', portrait='Чернігів - набрався вже в Букі - Одеса не цікаво бо прильоти - Вінниця+дзвінок', diagnosis='запит', offer='Вінниця', sortOrder=7),
    dict(name='Людмила Yeg', phone='+380 (67) 466-82-50', stage='qualified', portrait='Знає Едем в Львові. Спілкувались за вол рібас вінниця', diagnosis='вивчає', sortOrder=8),
    dict(name='Сергій', phone='+380 (98) 711-14-36', stage='qualified', portrait='Чув за лелеку шось / Київ / Одеса далеко - без зв', sortOrder=9),
    dict(name='Вікторія Андрощук', phone='+380 (97) 342-52-64', stage='qualified', portrait='Знайома з Одесою / каже заморозити кошти не дуже хотілось, Одесу вона не розглядала а Буковель то відпочинок хоч і тд. Цифри цікаві і лелеку теж розповіла', notes='26.07 - спеціально не відкриває час бо немає часу, з понеділка пробуємо планувати зум', sortOrder=10),
    dict(name='Леонід', phone='+380 (67) 460-53-83', stage='qualified', prevContact='під Києвом', portrait='цікаво та якби ще так було', notes="17.06 - відправила сценарії; 25.06 - розсилка інтерв'ю ОС", sortOrder=11),
    dict(name='Віктор', phone='+380 (67) 630-38-46', stage='qualified', portrait='17.06 - скиньте я подивлюсь Одесу і повернутись наступного тижня, все в тг', sortOrder=12),
    dict(name='Максим Грандкар Слищенко', phone='@Maksimilingus', stage='qualified', portrait='Вінниця / гляне Одесу, лелеку, ціна квадрат?', sortOrder=13),
    dict(name='ДАНІК', phone='danildanu', stage='qualified', sortOrder=14),
    dict(name='Віталій Павленко', phone='+380 (67) 431-88-82', stage='qualification', portrait='Вінниця / Київ - ігнорує', diagnosis='пауза', sortOrder=15),
    dict(name='Ігор Шептяков', phone='+380 (98) 228-56-63', stage='qualification', portrait='Вінниця / чув про лелеку / цікаво', sortOrder=16),
    dict(name='Олександр', phone='+380 (93) 041-92-04', stage='qualification', portrait='М. Вінниця - Тг 0636584335', sortOrder=17),
    dict(name='Віктор', phone='+380 (67) 144-74-77', stage='qualification', prevContact='Київ', portrait='Сам хоче займатись будівництвом таунхаусів. Знайомий займається багатоповерховими будинками. Каже - важко прорахувати зараз м.кв', sortOrder=18),
    dict(name='Віталій', phone='+380 (96) 787-07-52', stage='qualification', prevContact='інф в тг', portrait='Вінниця, знайомий з Одесою', offer='Leleka', sortOrder=19),
    dict(name='Віталій', phone='+380 (97) 753-05-52', stage='qualification', offer='Leleka', proposal='Які гарантії? Як він захищений?', sortOrder=20),
    dict(name='Дмитрук Богдан', phone='0 50 311 58 93', stage='inactive', nextAction='Розсилка: перевірити, чи стало актуально', nextActionAt='2027-03-11', sortOrder=21),
    dict(name='Наталя Опалко', phone='0 66 038 99 94', stage='cold', sortOrder=22),
    dict(name='Андрій', phone='0 93 448 43 13', stage='cold', notes='Вол', sortOrder=23),
    dict(name='Станіслав', phone='0 50 307 56 22', stage='cold', sortOrder=24),
    dict(name='Наталі', phone='0 50 819 90 03', stage='cold', sortOrder=25),
    dict(name='Олексій', phone='0 67 243 99 99', stage='cold', sortOrder=26),
    dict(name='Вхідний', phone='0 63 812 01 03', stage='cold', sortOrder=27),
    dict(name='Артем Смоглий', phone='0 95 270 59 89', stage='cold', sortOrder=28),
    dict(name='Дмитро Кісельов', phone='0 67 263 52 20', stage='cold', sortOrder=29),
    dict(name='Ярослав Герас', phone='0 98 006 66 36', stage='cold', sortOrder=30),
    dict(name='Юрій', phone='0 67 263 79 02', stage='cold', sortOrder=31),
    dict(name='Андрій', phone='0 50 402 63 00', stage='cold', sortOrder=32),
    dict(name='Максим Заіка', phone='0 67 571 79 71', stage='cold', sortOrder=33),
    dict(name='Микола Кремен', phone='0 98 945 33 41', stage='cold', sortOrder=34),
    dict(name='Денис', phone='0 67 559 98 99', stage='cold', sortOrder=35),
    dict(name='Жнець Михайло', phone='0 98 336 99 99', stage='cold', sortOrder=36),
    dict(name='Андрій', phone='0 96 417 34 15', stage='cold', sortOrder=37),
    dict(name='Анна Набок', phone='0 96 496 96 69', stage='cold', sortOrder=38),
    dict(name='Оксана', phone='0 99 750 02 60', stage='cold', sortOrder=39),
    dict(name='Катерина Осташ', phone='0 63 122 66 04', stage='cold', sortOrder=40),
    dict(name='Ольга', phone='0 50 302 27 39', stage='cold', sortOrder=41),
    dict(name='Катерина Гаєвська', phone='0 93 616 56 69', stage='cold', sortOrder=42),
    dict(name='Павло', phone='0 93 164 99 63', stage='cold', sortOrder=43),
    dict(name='Глущенко', phone='0 73 199 25 56', stage='cold', sortOrder=44),
    dict(name='Наталя', phone='0 67 348 15 42', stage='cold', sortOrder=45),
    dict(name='Вікторія Данилюк', phone='0 97 941 40 31', stage='cold', sortOrder=46),
    dict(name='Дмитро', phone='0 50 486 44 03', stage='cold', sortOrder=47),
    dict(name='Стас', phone='0 50 307 56 22', stage='cold', sortOrder=48),
    dict(name='Віталій Турин', phone='0 67 577 74 34', stage='cold', sortOrder=49),
    dict(name='Євгенія', phone='0 67 401 38 80', stage='cold', sortOrder=50),
    dict(name='Олексій', phone='0 50 415 31 30', stage='cold', sortOrder=51),
    dict(name='Дмитро', phone='0 67 224 67 76', stage='cold', sortOrder=52),
    dict(name='Олексій', phone='0 66 000 23 23', stage='cold', sortOrder=53),
    dict(name='Олександр', phone='0 50 337 13 86', stage='cold', sortOrder=54),
    dict(name='Анатолій', phone='0 63 881 94 61', stage='cold', sortOrder=55),
    dict(name='Ольга', phone='0 67 989 27 90', stage='cold', sortOrder=56),
    dict(name='Ніна', phone='0 97 456 05 83', stage='cold', notes='Вінниця вол', sortOrder=57),
    dict(name='Морозива Анна', phone='+380 (67) 378-80-12', stage='client', dealInfo='Купила WOL апарт 417 (2770$×30=85к$)', sortOrder=58),
    dict(name='Сіверс', phone='+380 (67) 460-55-48', stage='client', dealInfo='WOL 316 - 100к$', sortOrder=59),
    dict(name='Біблий', phone='+380 (68) 798-98-29', stage='cold', notes='Взято з переліку без підтвердженої угоди', sortOrder=60),
    dict(name='Балич Ігор', phone='balych22@gmail.com', stage='client', dealInfo='Ама2.0 / 3900$ / 407=108тис$', sortOrder=61),
    dict(name='Олена Горбатова', phone='+380 (63) 674-27-44', stage='client', dealInfo='Переуступку Романа', sortOrder=62),
    dict(name='Філіпенко Олена', phone='067-539-09-40', stage='client', dealInfo='Потай буд.60', sortOrder=63),
    dict(name='Оксана', phone='+380 (50) 524-69-36', stage='client', dealInfo='Потай на дочку, Злетів, аванс', sortOrder=64),
    dict(name='Вишнівський Микола', phone='+380 (67) 691-77-91', stage='client', dealInfo='Злетів, аванс, вол', sortOrder=65),
    dict(name='Астапенков Володимир', phone='(067) 551-62-59', stage='cold', notes='Взято з переліку без підтвердженої угоди', sortOrder=66),
    dict(name='Сушко Костянтин', phone='+380 (50) 476-36-01', stage='client', dealInfo='Аванс, ама 2', sortOrder=67),
    dict(name='Леонід Катрук', phone='0 (93) 405-28-22', stage='cold', notes='Взято з переліку без підтвердженої угоди', sortOrder=68),
    dict(name='Яцина Ганна', phone='+380 (99) 537-60-39', stage='cold', dealInfo='Спа рест', sortOrder=69),
]


def run():
    db.init_db()
    if db.list_leads():
        print("Таблиця leads не порожня — пропускаю сідування.")
        return
    for lead in LEADS:
        db.create_lead(lead)
    print(f"Додано {len(LEADS)} лідів.")


if __name__ == "__main__":
    run()
