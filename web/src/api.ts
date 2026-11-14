export const mockEvents = [
  {
    id: 1,
    title: "ТПУ — соорганизатор олимпиады «Я – профессионал»",
    organizer: "ТПУ | Томский политехнический университет",
    category: "science",
    date: "2026-11-13",
    end_date: "2026-11-29",
    time: null,
    location: null,
    is_online: false,
    vk_post_url: "https://vk.com/tpu_official",
    description: "Крупнейшая олимпиада для студентов. Несколько направлений: IT, инженерия, естественные науки."
  },
  {
    id: 2,
    title: "Дайджест выходного дня",
    organizer: "Команда ТПУ",
    category: "science",
    date: "2026-11-15",
    end_date: null,
    time: "18:25",
    location: "Корпус X, лекторий",
    is_online: false,
    vk_post_url: "https://vk.com/tpu_official",
    description: "Обзор главных событий недели."
  }
];

export async function fetchEvents() {
  try {
    const response = await fetch('/api/events');
    if (!response.ok) throw new Error('API error');
    return await response.json();
  } catch {
    console.warn("API недоступен, используем мок-данные");
    return mockEvents;
  }
}
