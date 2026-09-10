"""One-off seed of the leads captured from the original CRM export.

Run manually: `python seed.py`. Safe to re-run — skips seeding if the
leads table already has rows, so it never duplicates data.
"""
import db

LEADS = [
    dict(name="Ігор Турцевич", phone="+380 (67) 656-51-11", stage="investor",
         portrait="Білорусь - Київ - досвід", diagnosis="ОФФЕР", offer="ArcHotel",
         decision="Угода (очікується)", notes="ArcHotel 05.2026 · ArcHotel 18.08"),
    dict(name="Віктор Яблуниця", phone="0 (67) 570-23-56", stage="qualified",
         prev_contact="16 серпня буде в Укр"),
    dict(name="Андрій", phone="+380 (50) 471-53-15", stage="qualified",
         portrait="Варна цікавить тільки за кордон - скинути",
         notes="24.06 - дзвінок, скидаю на вайбер ВАРНУ, дітей каже краз туди везе",
         diagnosis="Передача ліда", offer="Arcanum"),
    dict(name="Вікторія", phone="+380 (93) 712-92-71", stage="qualified",
         portrait="24.06 - скинути варну, дуже цікавить Болгарія а не Одеса в межах 50 тисяч",
         diagnosis="Передача ліда", offer="Arcanum"),
    dict(name="Наталя", phone="+380 (97) 471-85-29", stage="qualified",
         portrait="Львів - вайбер - покупка на осінь +- - і капіталізація і пасив - закордон не цікаво, Київ страшно",
         diagnosis="ОФФЕР", offer="MOVIN"),
    dict(name="Ігор Ама", phone="+380 (50) 330-87-40", stage="qualified",
         portrait="Пасив - від 100 - Київ - досвід жк Київ Одеса", diagnosis="заперечення", offer="MIY"),
    dict(name="Роман", phone="+380 (97) 486-41-35", stage="qualified", prev_contact="пон. 17:00",
         portrait="Чернігів - набрався вже в Букі - Одеса не цікаво бо прильоти - Вінниця+дзвінок",
         diagnosis="запит", offer="Вінниця"),
    dict(name="Людмила Yeg", phone="+380 (67) 466-82-50", stage="qualified",
         portrait="Знає Едем в Львові. Спілкувались за вол рібас вінниця", diagnosis="вивчає"),
    dict(name="Сергій", phone="+380 (98) 711-14-36", stage="qualified",
         portrait="Чув за лелеку шось / Київ / Одеса далеко - без зв"),
    dict(name="Вікторія Андрощук", phone="+380 (97) 342-52-64", stage="qualified",
         portrait="Знайома з Одесою / каже заморозити кошти не дуже хотілось, Одесу вона не розглядала "
                   "а Буковель то відпочинок хоч і тд. Цифри цікаві і лелеку теж розповіла",
         notes="26.07 - спеціально не відкриває час бо немає часу, з понеділка пробуємо планувати зум"),
    dict(name="Леонід", phone="+380 (67) 460-53-83", stage="qualified", prev_contact="під Києвом",
         portrait="цікаво та якби ще так було",
         notes="17.06 - відправила сценарії; 25.06 - розсилка інтерв'ю ОС"),
    dict(name="Віктор", phone="+380 (67) 630-38-46", stage="qualified",
         portrait="17.06 - скиньте я подивлюсь Одесу і повернутись наступного тижня, все в тг"),
    dict(name="Максим Грандкар Слищенко", phone="@Maksimilingus", stage="qualified",
         portrait="Вінниця / гляне Одесу, лелеку, ціна квадрат?"),
    dict(name="ДАНІК", phone="danildanu", stage="qualified"),
    dict(name="Віталій Павленко", phone="+380 (67) 431-88-82", stage="qualification",
         portrait="Вінниця / Київ - ігнорує", diagnosis="пауза"),
    dict(name="Ігор Шептяков", phone="+380 (98) 228-56-63", stage="qualification",
         portrait="Вінниця / чув про лелеку / цікаво"),
    dict(name="Олександр", phone="+380 (93) 041-92-04", stage="qualification",
         portrait="М. Вінниця - Тг 0636584335"),
    dict(name="Віктор", phone="+380 (67) 144-74-77", stage="qualification", prev_contact="Київ",
         portrait="Сам хоче займатись будівництвом таунхаусів. Знайомий займається багатоповерховими "
                   "будинками. Каже - важко прорахувати зараз м.кв"),
    dict(name="Віталій", phone="+380 (96) 787-07-52", stage="qualification", prev_contact="інф в тг",
         portrait="Вінниця, знайомий з Одесою", offer="Leleka"),
    dict(name="Віталій", phone="+380 (97) 753-05-52", stage="qualification", offer="Leleka",
         proposal="Які гарантії? Як він захищений?"),

    dict(name="Дмитрук Богдан", phone="0 50 311 58 93", stage="cold"),
    dict(name="Наталя Опалко", phone="0 66 038 99 94", stage="cold"),
    dict(name="Андрій", phone="0 93 448 43 13", stage="cold", notes="Вол"),
    dict(name="Станіслав", phone="0 50 307 56 22", stage="cold"),
    dict(name="Наталі", phone="0 50 819 90 03", stage="cold"),
    dict(name="Олексій", phone="0 67 243 99 99", stage="cold"),
    dict(name="Вхідний", phone="0 63 812 01 03", stage="cold"),
    dict(name="Артем Смоглий", phone="0 95 270 59 89", stage="cold"),
    dict(name="Дмитро Кісельов", phone="0 67 263 52 20", stage="cold"),
    dict(name="Ярослав Герас", phone="0 98 006 66 36", stage="cold"),
    dict(name="Юрій", phone="0 67 263 79 02", stage="cold"),
    dict(name="Андрій", phone="0 50 402 63 00", stage="cold"),
    dict(name="Максим Заіка", phone="0 67 571 79 71", stage="cold"),
    dict(name="Микола Кремен", phone="0 98 945 33 41", stage="cold"),
    dict(name="Денис", phone="0 67 559 98 99", stage="cold"),
    dict(name="Жнець Михайло", phone="0 98 336 99 99", stage="cold"),
    dict(name="Андрій", phone="0 96 417 34 15", stage="cold"),
    dict(name="Анна Набок", phone="0 96 496 96 69", stage="cold"),
    dict(name="Оксана", phone="0 99 750 02 60", stage="cold"),
    dict(name="Катерина Осташ", phone="0 63 122 66 04", stage="cold"),
    dict(name="Ольга", phone="0 50 302 27 39", stage="cold"),
    dict(name="Катерина Гаєвська", phone="0 93 616 56 69", stage="cold"),
    dict(name="Павло", phone="0 93 164 99 63", stage="cold"),
    dict(name="Глущенко", phone="0 73 199 25 56", stage="cold"),
    dict(name="Наталя", phone="0 67 348 15 42", stage="cold"),
    dict(name="Вікторія Данилюк", phone="0 97 941 40 31", stage="cold"),
    dict(name="Дмитро", phone="0 50 486 44 03", stage="cold"),
    dict(name="Стас", phone="0 50 307 56 22", stage="cold"),
    dict(name="Віталій Турин", phone="0 67 577 74 34", stage="cold"),
    dict(name="Євгенія", phone="0 67 401 38 80", stage="cold"),
    dict(name="Олексій", phone="0 50 415 31 30", stage="cold"),
    dict(name="Дмитро", phone="0 67 224 67 76", stage="cold"),
    dict(name="Олексій", phone="0 66 000 23 23", stage="cold"),
    dict(name="Олександр", phone="0 50 337 13 86", stage="cold"),
    dict(name="Анатолій", phone="0 63 881 94 61", stage="cold"),
    dict(name="Ольга", phone="0 67 989 27 90", stage="cold"),
    dict(name="Ніна", phone="0 97 456 05 83", stage="cold", notes="Вінниця вол"),
    dict(name="Біблий", phone="+380 (68) 798-98-29", stage="cold",
         notes="Взято з переліку без підтвердженої угоди"),
    dict(name="Астапенков Володимир", phone="(067) 551-62-59", stage="cold",
         notes="Взято з переліку без підтвердженої угоди"),
    dict(name="Леонід Катрук", phone="0 (93) 405-28-22", stage="cold",
         notes="Взято з переліку без підтвердженої угоди"),

    dict(name="Морозива Анна", phone="+380 (67) 378-80-12", stage="client",
         deal_info="Купила WOL апарт 417 (2770$×30=85к$)"),
    dict(name="Сіверс", phone="+380 (67) 460-55-48", stage="client", deal_info="WOL 316 - 100к$"),
    dict(name="Балич Ігор", phone="balych22@gmail.com", stage="client",
         deal_info="Ама2.0 / 3900$/м² / 407 = 108тис$"),
    dict(name="Олена Горбатова", phone="+380 (63) 674-27-44", stage="client", deal_info="Переуступка Романа"),
    dict(name="Філіпенко Олена", phone="067-539-09-40", stage="client", deal_info="Потай, буд. 60"),
    dict(name="Оксана", phone="+380 (50) 524-69-36", stage="client", deal_info="Потай на дочку, Злетів, аванс"),
    dict(name="Вишнівський Микола", phone="+380 (67) 691-77-91", stage="client", deal_info="Злетів, аванс, WOL"),
    dict(name="Сушко Костянтин", phone="+380 (50) 476-36-01", stage="client", deal_info="Аванс, Ама2"),
    dict(name="Яцина Ганна", phone="+380 (99) 537-60-39", stage="client", deal_info="Спа-ресторан"),
]


def run():
    db.init_db()
    if db.list_leads():
        print("Таблиця leads не порожня — пропускаю сідування.")
        return
    for lead in LEADS:
        lead.setdefault("source", "import")
        db.create_lead(lead)
    print(f"Додано {len(LEADS)} лідів.")


if __name__ == "__main__":
    run()
