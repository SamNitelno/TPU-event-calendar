export type CategoryId = "science" | "sport" | "culture" | "career" | "volunteer" | "student";

export type EventSource = "vk" | "form";

export interface TpuEvent {
  id: string;
  title: string;
  description: string;
  category: CategoryId;
  date: string; // YYYY-MM-DD
  endDate?: string;
  timeStart: string; // HH:MM
  timeEnd?: string;
  place: string;
  organizer: string;
  vkUrl: string;
  source: EventSource;
}

export type SubmissionStatus = "pending" | "approved" | "rejected";

export interface Submission extends TpuEvent {
  status: SubmissionStatus;
  contact: string;
  submittedAt: string; // YYYY-MM-DD
  rejectReason?: string;
}

export interface Category {
  id: CategoryId;
  slug: string;
  label: string;
  icon: string;
  chip: string; // classes for tinted chip
}

export const CATEGORIES: Category[] = [
  { id: "science", slug: "science", label: "Наука", icon: "FlaskConical", chip: "bg-cat-science text-cat-science-fg" },
  { id: "sport", slug: "sport", label: "Спорт", icon: "Trophy", chip: "bg-cat-sport text-cat-sport-fg" },
  { id: "culture", slug: "creativity", label: "Культура", icon: "Music", chip: "bg-cat-culture text-cat-culture-fg" },
  { id: "career", slug: "career", label: "Карьера", icon: "Briefcase", chip: "bg-cat-career text-cat-career-fg" },
  { id: "volunteer", slug: "volunteering", label: "Волонтёрство", icon: "HeartHandshake", chip: "bg-cat-volunteer text-cat-volunteer-fg" },
  { id: "student", slug: "student_life", label: "Студенческая жизнь", icon: "Users", chip: "bg-cat-student text-cat-student-fg" },
];

export const categoryBySlug = (slug: string): Category =>
  CATEGORIES.find((c) => c.slug === slug) ?? CATEGORIES[CATEGORIES.length - 1];

export const categoryById = (id: CategoryId): Category =>
  CATEGORIES.find((c) => c.id === id) ?? CATEGORIES[0];

export const MONTHS_GEN = [
  "января", "февраля", "марта", "апреля", "мая", "июня",
  "июля", "августа", "сентября", "октября", "ноября", "декабря",
];
export const MONTHS_NOM = [
  "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
  "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
];
export const WEEKDAYS = ["воскресенье", "понедельник", "вторник", "среда", "четверг", "пятница", "суббота"];
export const WEEKDAYS_SHORT = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];

/** Fixed reference date used for server render; client replaces it with the real date. */
export const REFERENCE_TODAY = "2026-10-27";

export const parseDate = (iso: string) => {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d);
};

export const toIso = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

export const formatLongDate = (iso: string) => {
  const d = parseDate(iso);
  return `${d.getDate()} ${MONTHS_GEN[d.getMonth()]}, ${WEEKDAYS[d.getDay()]}`;
};

export const formatTime = (e: Pick<TpuEvent, "timeStart" | "timeEnd">) =>
  !e.timeStart ? "Весь день" : e.timeEnd ? `${e.timeStart} – ${e.timeEnd}` : e.timeStart;

export const lastDay = (e: Pick<TpuEvent, "date" | "endDate">) => e.endDate ?? e.date;

export const SEED_EVENTS: TpuEvent[] = [
  {
    id: "e1", title: "Хакатон «Энергия кода»", category: "science", date: "2026-10-28",
    timeStart: "10:00", timeEnd: "20:00", place: "Корпус 10, коворкинг",
    organizer: "Клуб «Наука и инновации»", vkUrl: "https://vk.com/tpunews", source: "vk",
    description: "Десятичасовой командный хакатон по задачам энергетики и цифровых двойников. Команды по 3–5 человек, менторы от индустриальных партнёров, призовой фонд.",
  },
  {
    id: "e2", title: "Турнир по волейболу", category: "sport", date: "2026-10-28",
    timeStart: "18:30", place: "Спорткомплекс, зал 2", organizer: "Спортклуб ТПУ",
    vkUrl: "https://vk.com/tpunews", source: "vk",
    description: "Межфакультетский турнир по волейболу среди смешанных команд. Болельщики приветствуются, вход свободный.",
  },
  {
    id: "e3", title: "Встреча с ректором", category: "student", date: "2026-10-30",
    timeStart: "16:00", timeEnd: "17:30", place: "Главный корпус, ауд. 201",
    organizer: "Студенческий совет", vkUrl: "https://vk.com/tpunews", source: "vk",
    description: "Открытый разговор о жизни университета: общежития, расписание, студенческие инициативы. Вопросы можно задать заранее в комментариях к посту.",
  },
  {
    id: "e4", title: "Ярмарка вакансий «Карьера в энергетике»", category: "career", date: "2026-10-31",
    timeStart: "11:00", timeEnd: "16:00", place: "Корпус 8, атриум",
    organizer: "Центр карьеры ТПУ", vkUrl: "https://vk.com/tpunews", source: "vk",
    description: "Более 30 компаний-работодателей, стажировки и летние практики. Возьмите с собой резюме — консультанты помогут его доработать на месте.",
  },
  {
    id: "e5", title: "Субботник в Ботаническом саду", category: "volunteer", date: "2026-11-01",
    timeStart: "10:00", timeEnd: "13:00", place: "Сибирский ботанический сад",
    organizer: "Волонтёрский центр ТПУ", vkUrl: "https://vk.com/tpunews", source: "vk",
    description: "Помогаем подготовить сад к зиме. Перчатки и инвентарь выдаём, горячий чай — обязательно.",
  },
  {
    id: "e6", title: "Концерт «Осенний джаз»", category: "culture", date: "2026-11-02",
    timeStart: "19:00", timeEnd: "21:00", place: "Дворец культуры ТПУ",
    organizer: "Студенческий клуб", vkUrl: "https://vk.com/tpunews", source: "vk",
    description: "Вечер джазовых стандартов в исполнении студенческого биг-бэнда и приглашённых музыкантов.",
  },
  {
    id: "e7", title: "Лекция «Водородная энергетика»", category: "science", date: "2026-11-03",
    timeStart: "15:00", timeEnd: "16:30", place: "Корпус 4, ауд. 112",
    organizer: "Инженерная школа энергетики", vkUrl: "https://vk.com/tpunews", source: "vk",
    description: "Открытая лекция о технологиях получения и хранения водорода и о том, где в этой отрасли нужны инженеры.",
  },
  {
    id: "e8", title: "Забег «Политех в движении»", category: "sport", date: "2026-11-05",
    timeStart: "09:00", place: "Старт у Главного корпуса", organizer: "Спортклуб ТПУ",
    vkUrl: "https://vk.com/tpunews", source: "vk",
    description: "Дистанции 3 и 5 км по центру Томска. Регистрация участников на месте старта за час до забега.",
  },
  {
    id: "e9", title: "Мастер-класс по публичным выступлениям", category: "career", date: "2026-11-05",
    timeStart: "17:00", timeEnd: "19:00", place: "Корпус 10, ауд. 305",
    organizer: "Центр карьеры ТПУ", vkUrl: "https://vk.com/tpunews", source: "vk",
    description: "Как держаться на защите проекта и на собеседовании: практика выступлений с обратной связью.",
  },
  {
    id: "e10", title: "Посвящение в первокурсники", category: "student", date: "2026-11-07",
    timeStart: "18:00", timeEnd: "22:00", place: "Дворец культуры ТПУ",
    organizer: "Студенческий совет", vkUrl: "https://vk.com/tpunews", source: "vk",
    description: "Главный праздник первокурсников: квест по факультетам, концерт и дискотека.",
  },
  {
    id: "e11", title: "Донорская акция", category: "volunteer", date: "2026-11-10",
    timeStart: "09:00", timeEnd: "13:00", place: "Главный корпус, холл",
    organizer: "Волонтёрский центр ТПУ", vkUrl: "https://vk.com/tpunews", source: "vk",
    description: "Выездная бригада областной станции переливания крови. Перед сдачей — лёгкий завтрак, с собой паспорт.",
  },
  {
    id: "e12", title: "Научный семинар «Материалы будущего»", category: "science", date: "2026-11-12",
    timeStart: "14:00", timeEnd: "17:00", place: "Корпус 2, конференц-зал",
    organizer: "Клуб «Наука и инновации»", vkUrl: "https://vk.com/tpunews", source: "vk",
    description: "Доклады аспирантов о композитах, покрытиях и аддитивных технологиях. Можно выступить со своим постером.",
  },
  {
    id: "e13", title: "Кинопоказ и обсуждение", category: "culture", date: "2026-11-13",
    timeStart: "19:00", place: "Корпус 10, кинозал", organizer: "Киноклуб «Кадр»",
    vkUrl: "https://vk.com/tpunews", source: "vk",
    description: "Смотрим фильм и обсуждаем его с приглашённым кинокритиком. Попкорн за счёт клуба.",
  },
  {
    id: "e14", title: "День открытых дверей", category: "student", date: "2026-11-15",
    timeStart: "11:00", timeEnd: "15:00", place: "Главный корпус",
    organizer: "Приёмная комиссия", vkUrl: "https://vk.com/tpunews", source: "vk",
    description: "Экскурсии по лабораториям, встречи с преподавателями и студентами всех инженерных школ.",
  },
  {
    id: "e15", title: "Кубок ТПУ по мини-футболу", category: "sport", date: "2026-11-18",
    timeStart: "17:00", place: "Спорткомплекс, большой зал", organizer: "Спортклуб ТПУ",
    vkUrl: "https://vk.com/tpunews", source: "vk",
    description: "Финальная часть кубка. Восемь команд, плей-офф, награждение лучших игроков.",
  },
  {
    id: "e16", title: "Карьерный завтрак с выпускниками", category: "career", date: "2026-11-20",
    timeStart: "09:30", timeEnd: "11:00", place: "Корпус 8, кафе",
    organizer: "Ассоциация выпускников", vkUrl: "https://vk.com/tpunews", source: "vk",
    description: "Неформальная встреча с выпускниками, которые работают в крупных инженерных компаниях.",
  },
  {
    id: "e17", title: "Спектакль студенческого театра", category: "culture", date: "2026-11-21",
    timeStart: "18:30", place: "Дворец культуры ТПУ", organizer: "Театр «Политех»",
    vkUrl: "https://vk.com/tpunews", source: "vk",
    description: "Премьера новой постановки студенческого театра. Вход свободный, места ограничены.",
  },
  {
    id: "e18", title: "Сбор вещей для приюта", category: "volunteer", date: "2026-11-24",
    timeStart: "10:00", timeEnd: "18:00", place: "Общежитие № 9, холл",
    organizer: "Волонтёрский центр ТПУ", vkUrl: "https://vk.com/tpunews", source: "vk",
    description: "Принимаем корм, пледы и миски для приюта животных «Верность».",
  },
  {
    id: "e19", title: "Конференция молодых учёных", category: "science", date: "2026-11-26",
    timeStart: "10:00", timeEnd: "18:00", place: "Главный корпус, актовый зал",
    organizer: "Совет молодых учёных", vkUrl: "https://vk.com/tpunews", source: "vk",
    description: "Пленарная сессия и секции по направлениям. Лучшие доклады будут рекомендованы к публикации.",
  },
  {
    id: "e20", title: "Новогодний бал — старт подготовки", category: "student", date: "2026-11-28",
    timeStart: "16:00", place: "Корпус 10, ауд. 101", organizer: "Студенческий совет",
    vkUrl: "https://vk.com/tpunews", source: "vk",
    description: "Собираем команду организаторов бала: сценаристы, дизайнеры, ведущие и техническая группа.",
  },
  {
    id: "e21", title: "Шахматный турнир", category: "sport", date: "2026-12-02",
    timeStart: "15:00", place: "Корпус 3, ауд. 210", organizer: "Шахматный клуб ТПУ",
    vkUrl: "https://vk.com/tpunews", source: "vk",
    description: "Быстрые шахматы, швейцарская система, 7 туров. Подходит для любого уровня.",
  },
  {
    id: "e22", title: "Выставка «Инженерное искусство»", category: "culture", date: "2026-12-04",
    timeStart: "12:00", timeEnd: "19:00", place: "Музей ТПУ",
    organizer: "Музейный комплекс ТПУ", vkUrl: "https://vk.com/tpunews", source: "vk",
    description: "Чертежи, модели и фотографии из истории университета рядом с работами современных студентов.",
  },
];

export const SEED_SUBMISSIONS: Submission[] = [
  {
    id: "s1", title: "Квиз «Знаешь ли ты Томск?»", category: "student", date: "2026-11-06",
    timeStart: "19:00", timeEnd: "21:00", place: "Корпус 10, коворкинг",
    organizer: "Клуб интеллектуальных игр", vkUrl: "https://vk.com/tpunews", source: "form",
    description: "Командный квиз по истории и достопримечательностям города. Команды до 6 человек.",
    status: "pending", contact: "quiz.tpu@example.ru", submittedAt: "2026-10-25",
  },
  {
    id: "s2", title: "Робототехнический батл", category: "science", date: "2026-11-14",
    timeStart: "12:00", timeEnd: "17:00", place: "Корпус 16, лаборатория робототехники",
    organizer: "Клуб робототехники", vkUrl: "https://vk.com/tpunews", source: "vk",
    description: "Соревнования роботов-сумоистов и гонки по линии. Найдено автоматически в сообществе ВКонтакте.",
    status: "pending", contact: "vk.com/tpu_robots", submittedAt: "2026-10-26",
  },
  {
    id: "s3", title: "Йога в общежитии", category: "sport", date: "2026-11-09",
    timeStart: "08:00", place: "Общежитие № 5, спортзал",
    organizer: "Студсовет общежитий", vkUrl: "https://vk.com/tpunews", source: "form",
    description: "Утренняя практика для всех желающих, коврики есть.",
    status: "pending", contact: "dorm5@example.ru", submittedAt: "2026-10-26",
  },
];
