import { NextResponse } from "next/server";

export async function GET(request: Request, { params }: { params: { id: string } }) {
  const id = params.id || "quantum-glass";

  let presentation: any = {};

  if (id === "quantum-obsidian") {
    // -------------------------------------------------------------
    // 2. Midnight Obsidian (Gold, Unbounded Cyrillic)
    // -------------------------------------------------------------
    presentation = {
      id: "quantum-obsidian",
      title: "Эра Квантового Превосходства & Защита Данных",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      data: null,
      file: "presentation.pptx",
      n_slides: 6,
      prompt: "Масштабируемые квантовые процессоры и криптография завтрашнего дня",
      summary: "Элитная презентация в стиле Obsidian о вычислениях нового поколения и квантовой защите.",
      theme: {
        curated_palette: "midnight_obsidian"
      },
      titles: ["Квантовое Превосходство", "Преимущества Бизнеса", "Экономический Эффект", "Квантовая Угроза", "Вычислительный Таймлайн", "Стратегия Перехода"],
      user_id: "user_obsidian",
      vector_store: null,
      thumbnail: "",
      slides: [
        {
          index: 0,
          type: "title",
          title: "КВАНТОВЫЕ ВЫЧИСЛЕНИЯ",
          content: "Масштабируемые процессоры нового поколения, квантовое превосходство и защита критических данных.",
          bullets: [],
          stats: [],
          images: ["https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=1280&h=720&fit=crop"],
          properties: {
            companyName: "OBSIDIAN QUANTUM LABS",
            logoUrl: "https://presenton-public.s3.ap-southeast-1.amazonaws.com/static/icons/bold/fediverse-logo-bold.svg"
          }
        },
        {
          index: 1,
          type: "bullets",
          title: "Преимущества для Глобального Бизнеса",
          content: "Квантовые алгоритмы превосходят классические суперкомпьютеры в решении сложнейших вычислительных задач.",
          bullets: [
            "Оптимизация портфелей: Проведение финансовых расчетов с миллионами переменных за миллисекунды.",
            "Моделирование молекул: Создание новых материалов, катализаторов и лекарств с нулевыми затратами на реальные тесты.",
            "Интеллектуальная логистика: Решение сложнейших многокритериальных задач маршрутизации в реальном времени.",
            "Сверхмощный AI: Ускорение обучения сложнейших нейросетей на квантовых симуляторах в тысячи раз."
          ],
          stats: [],
          images: ["https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?q=80&w=1280&h=720&fit=crop"],
          icons: [
            "https://presenton-public.s3.ap-southeast-1.amazonaws.com/static/icons/bold/checks-bold.svg",
            "https://presenton-public.s3.ap-southeast-1.amazonaws.com/static/icons/bold/checks-bold.svg",
            "https://presenton-public.s3.ap-southeast-1.amazonaws.com/static/icons/bold/checks-bold.svg",
            "https://presenton-public.s3.ap-southeast-1.amazonaws.com/static/icons/bold/checks-bold.svg"
          ]
        },
        {
          index: 2,
          type: "stats",
          title: "Экономический Эффект Внедрения",
          content: "Прогнозируемый рост глобального рынка квантовых технологий и ключевые индикаторы превосходства.",
          bullets: [],
          stats: [
            { value: "$1.3T", label: "Прогнозируемая ценность к 2035 г." },
            { value: "1000x", label: "Ускорение криптографических расчетов" },
            { value: "1M+", label: "Физических кубитов в чипе к 2028 г." },
            { value: "#1", label: "Приоритет национальной безопасности" }
          ],
          images: ["https://images.unsplash.com/photo-1518770660439-4636190af475?q=80&w=1280&h=720&fit=crop"]
        },
        {
          index: 3,
          type: "quote",
          title: "Философия Новой Эпохи",
          content: "«Те, кто первыми овладеют масштабируемыми квантовыми компьютерами, получат ключи от всех зашифрованных тайн мира. Это технологическая гонка, где второе место означает полное поражение.»",
          bullets: [
            "Доктор Чарльз Беннетт, Соавтор фундаментального квантового протокола BB84"
          ],
          stats: [],
          images: ["https://images.unsplash.com/photo-1558494949-ef010cbdcc31?q=80&w=1280&h=720&fit=crop"]
        },
        {
          index: 4,
          type: "timeline",
          title: "Развитие Квантовых Вычислений",
          content: "Ключевые вехи масштабирования физических кубитов и стабилизации логических вентилей.",
          bullets: [
            "2024: Достижение стабильности 100+ логических кубитов с глубокой коррекцией ошибок.",
            "2026: Первое коммерческое применение в фармакологии для моделирования сложных белков.",
            "2028: Создание первого отказоустойчивого процессора на миллион физических кубитов.",
            "2030+: Запуск облачных квантовых вычислений общего назначения по модели QaaS."
          ],
          stats: [],
          images: ["https://images.unsplash.com/photo-1451187580459-43490279c0fa?q=80&w=1280&h=720&fit=crop"]
        },
        {
          index: 5,
          type: "closing",
          title: "Защитите Свои Данные Уже Сегодня",
          content: "Появление квантового компьютера взломает существующие стандарты шифрования RSA и ECC. Начните переход на квантово-устойчивую криптографию (PQC) прямо сейчас, чтобы предотвратить компрометацию ваших корпоративных данных в будущем.",
          bullets: [],
          stats: [],
          images: ["https://images.unsplash.com/photo-1634017839464-5c339ebe3cb4?q=80&w=1280&h=720&fit=crop"],
          properties: {
            companyName: "OBSIDIAN QUANTUM LABS",
            logoUrl: "https://presenton-public.s3.ap-southeast-1.amazonaws.com/static/icons/bold/fediverse-logo-bold.svg"
          }
        }
      ]
    };
  } else if (id === "quantum-arctic") {
    // -------------------------------------------------------------
    // 3. Arctic Minimal (Sky Blue/Light Grey, Inter Cyrillic)
    // -------------------------------------------------------------
    presentation = {
      id: "quantum-arctic",
      title: "Чистые Технологии: Экологичный Квант",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      data: null,
      file: "presentation.pptx",
      n_slides: 6,
      prompt: "Энергоэффективные квантовые системы и экологический баланс вычислений",
      summary: "Светлая презентация в стиле Arctic Minimal о будущем «зеленых» квантовых вычислений.",
      theme: {
        curated_palette: "arctic_minimal"
      },
      titles: ["Экологичный Квант", "Базовые Физические Принципы", "Энергия и Экология", "Философия Простоты", "Зеленый Таймлайн", "Экологичное Будущее"],
      user_id: "user_arctic",
      vector_store: null,
      thumbnail: "",
      slides: [
        {
          index: 0,
          type: "title",
          title: "Зеленые Квантовые Системы",
          content: "Чистый взгляд на сложные процессы: как экологичные вычисления и энергоэффективные криостаты спасают планету.",
          bullets: [],
          stats: [],
          images: ["https://images.unsplash.com/photo-1517487881594-2787fef5ebf7?q=80&w=1280&h=720&fit=crop"],
          properties: {
            companyName: "ARCTIC GREEN COMPUTE",
            logoUrl: "https://presenton-public.s3.ap-southeast-1.amazonaws.com/static/icons/bold/fediverse-logo-bold.svg"
          }
        },
        {
          index: 1,
          type: "bullets",
          title: "Фундаментальные Принципы Чистоты",
          content: "Ключевые физические концепции квантовой механики, обеспечивающие невероятное быстродействие при минимальном энергопотреблении.",
          bullets: [
            "Суперпозиция: Уникальная способность кубита находиться во множестве состояний одновременно.",
            "Когерентность: Идеальная фазовая согласованность квантовых волн в изолированной среде.",
            "Защита от декогеренции: Предотвращение разрушения хрупких кубитов из-за теплового шума.",
            "Квантовая интерференция: Взаимное гашение ложных результатов и усиление истинных решений."
          ],
          stats: [],
          images: ["https://images.unsplash.com/photo-1498050108023-c5249f4df085?q=80&w=1280&h=720&fit=crop"],
          icons: [
            "https://presenton-public.s3.ap-southeast-1.amazonaws.com/static/icons/bold/checks-bold.svg",
            "https://presenton-public.s3.ap-southeast-1.amazonaws.com/static/icons/bold/checks-bold.svg",
            "https://presenton-public.s3.ap-southeast-1.amazonaws.com/static/icons/bold/checks-bold.svg",
            "https://presenton-public.s3.ap-southeast-1.amazonaws.com/static/icons/bold/checks-bold.svg"
          ]
        },
        {
          index: 2,
          type: "stats",
          title: "Показатели Эко-Эффективности",
          content: "Сравнение энергопотребления квантовых процессоров с традиционными мегаваттными дата-центрами.",
          bullets: [],
          stats: [
            { value: "95%", label: "Снижение расхода электроэнергии" },
            { value: "-50%", label: "Сокращение углеродного следа" },
            { value: "10 K", label: "Рабочая температура криостата" },
            { value: "24/7", label: "Непрерывный эко-мониторинг узлов" }
          ],
          images: ["https://images.unsplash.com/photo-1550751827-4bd374c3f58b?q=80&w=1280&h=720&fit=crop"]
        },
        {
          index: 3,
          type: "quote",
          title: "Простота как Главный Стандарт",
          content: "«Сложность должна быть полностью скрыта внутри физических процессов, в то время как снаружи пользователя должен встречать безупречный, понятный и экологически чистый минимализм.»",
          bullets: [
            "Дитер Рамс, Великий промышленный дизайнер и основоположник минимализма"
          ],
          stats: [],
          images: ["https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?q=80&w=1280&h=720&fit=crop"]
        },
        {
          index: 4,
          type: "timeline",
          title: "Зеленая Дорожная Карта",
          content: "План перехода вычислительной инфраструктуры к полной углеродной нейтральности.",
          bullets: [
            "2024: Сертификация инновационных криогенных систем замкнутого цикла без потери гелия.",
            "2026: Перевод научно-исследовательских квантовых узлов на автономную солнечную энергию.",
            "2028: Создание биоразлагаемых кремниевых подложек для экологичной утилизации чипов.",
            "2030+: Запуск 100% углеродно-нейтральной глобальной сети зеленых квантовых суперкомпьютеров."
          ],
          stats: [],
          images: ["https://images.unsplash.com/photo-1460925895917-afdab827c52f?q=80&w=1280&h=720&fit=crop"]
        },
        {
          index: 5,
          type: "closing",
          title: "Чистое Будущее Вычислений",
          content: "Экологическая трансформация ИТ — это не просто тренд, а необходимость. Начните оптимизацию своей инфраструктуры и переведите вычисления на экологичные рельсы вместе с технологиями Arctic Green Compute.",
          bullets: [],
          stats: [],
          images: ["https://images.unsplash.com/photo-1504384308090-c894fdcc538d?q=80&w=1280&h=720&fit=crop"],
          properties: {
            companyName: "ARCTIC GREEN COMPUTE",
            logoUrl: "https://presenton-public.s3.ap-southeast-1.amazonaws.com/static/icons/bold/fediverse-logo-bold.svg"
          }
        }
      ]
    };
  } else if (id === "academic" || id === "academic-quantum") {
    // -------------------------------------------------------------
    // 4. Academic Presentation (String Theory & Quantum Gravity, Midnight Glass)
    // -------------------------------------------------------------
    presentation = {
      id: "academic",
      title: "Теория струн, М-теория и квантовая гравитация",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      data: null,
      file: "presentation.pptx",
      n_slides: 6,
      prompt: "Теория струн, М-теория и проблемы квантовой гравитации",
      summary: "Академическая презентация экспертного уровня об объединении квантовой механики и общей теории относительности.",
      theme: {
        curated_palette: "midnight_glass"
      },
      titles: [
        "Объединение теорий",
        "Основные понятия",
        "Ключевые Метрики",
        "Проблемы гравитации",
        "Методология",
        "Перспективы и Резюме"
      ],
      user_id: "user_academic",
      vector_store: null,
      thumbnail: "",
      slides: [
        {
          index: 0,
          type: "title",
          title: "ТЕОРИЯ СТРУН И КВАНТОВАЯ ГРАВИТАЦИЯ",
          content: "Объединение квантовой механики и общей теории относительности в единую М-теорию. Фундаментальный взгляд на устройство пространства-времени.",
          bullets: [],
          stats: [],
          images: ["https://images.unsplash.com/photo-1462331940025-496dfbfc7564?q=80&w=1280&h=720&fit=crop"],
          properties: {
            companyName: "РОССИЙСКАЯ АКАДЕМИЯ НАУК",
            logoUrl: "https://presenton-public.s3.ap-southeast-1.amazonaws.com/static/icons/bold/fediverse-logo-bold.svg"
          }
        },
        {
          index: 1,
          type: "bullets",
          title: "Основные понятия теории струн",
          content: "Ключевые теоретические концепции, описывающие квантовую структуру пространства-времени на фундаментальном планковском масштабе.",
          bullets: [
            "Суперструны: 10-мерные расширения пространства-времени, объединяющие квантовую механику и общую теорию относительности на уровне колебаний одномерных протяженных объектов.",
            "М-теория: 11-мерная супергравитационная модель, объединяющая пять ранее конкурирующих суперструнных теорий в единый математический каркас, предложенный Эдвардом Виттеном.",
            "Голографический принцип: Соотношение между 10-мерным объемным пространством (AdS) и его 4-мерной границей (CFT), где физика объема полностью кодируется поведением границы.",
            "Квантовая запутанность пространства: Концепция, согласно которой сама геометрия пространства-времени возникает из квантовой запутанности фундаментальных степеней свободы."
          ],
          stats: [],
          images: ["https://images.unsplash.com/photo-1451187580459-43490279c0fa?q=80&w=1280&h=720&fit=crop"],
          icons: [
            "https://presenton-public.s3.ap-southeast-1.amazonaws.com/static/icons/bold/checks-bold.svg",
            "https://presenton-public.s3.ap-southeast-1.amazonaws.com/static/icons/bold/checks-bold.svg",
            "https://presenton-public.s3.ap-southeast-1.amazonaws.com/static/icons/bold/checks-bold.svg",
            "https://presenton-public.s3.ap-southeast-1.amazonaws.com/static/icons/bold/checks-bold.svg"
          ]
        },
        {
          index: 2,
          type: "stats",
          title: "Ключевые Метрики Квантовой Гравитации",
          content: "Статистические и фундаментальные параметры, определяющие масштабы и структуру современной квантовой космологии.",
          bullets: [],
          stats: [
            { value: "5", label: "Эквивалентных суперструнных теорий" },
            { value: "1995", label: "Год формулировки единой М-теории" },
            { value: "11D", label: "Размерность суперпространства М-теории" },
            { value: "10^-35", label: "Планковский масштаб длины (в метрах)" }
          ],
          images: ["https://images.unsplash.com/photo-1507668077129-56e32842fceb?q=80&w=1280&h=720&fit=crop"]
        },
        {
          index: 3,
          type: "bullets",
          title: "Проблемы Квантовой Гравитации",
          content: "Критический анализ ключевых концептуальных и экспериментальных барьеров на пути к созданию Единой Теории Всего.",
          bullets: [
            "Планковский масштаб: Необходимость исследования сверхмалых расстояний требует колоссальных энергий, недостижимых на современных коллайдерах.",
            "Проблема неперенормируемости: Попытки проквантовать ОТО классическими методами возмущений приводят к бесконечным расходимостям без физического смысла.",
            "Экспериментальный тупик: Отсутствие методов прямого наблюдения струн требует от теоретиков поиска косвенных космологических следствий в реликтовом излучении.",
            "Сценарии ландшафта: Огромное число ложных вакуумов в теории струн (до 10^500) снижает предсказательную силу теории и требует антропного принципа."
          ],
          stats: [],
          images: ["https://images.unsplash.com/photo-1635070041078-e363dbe005cb?q=80&w=1280&h=720&fit=crop"],
          icons: [
            "https://presenton-public.s3.ap-southeast-1.amazonaws.com/static/icons/bold/checks-bold.svg",
            "https://presenton-public.s3.ap-southeast-1.amazonaws.com/static/icons/bold/checks-bold.svg",
            "https://presenton-public.s3.ap-southeast-1.amazonaws.com/static/icons/bold/checks-bold.svg",
            "https://presenton-public.s3.ap-southeast-1.amazonaws.com/static/icons/bold/checks-bold.svg"
          ]
        },
        {
          index: 4,
          type: "quote",
          title: "Методологический Принцип Познания",
          content: "«Физики должны быть готовы отказаться от своих глубочайших убеждений и устоявшихся идей, если они вступают в неразрешимое противоречие с математической согласованностью Вселенной.»",
          bullets: [
            "Альберт Эйнштейн, Лауреат Нобелевской премии по физике, создатель Общей Теории Относительности"
          ],
          stats: [],
          images: ["https://images.unsplash.com/photo-1532094349884-543bc11b234d?q=80&w=1280&h=720&fit=crop"]
        },
        {
          index: 5,
          type: "closing",
          title: "Перспективы и Резюме Исследований",
          content: "Теория струн и М-теория представляют собой наиболее математически согласованные подходы к квантованию гравитационного поля. Хотя прямая экспериментальная верификация остается делом будущего, развитый математический аппарат уже привел к революционным открытиям в чистой математике и понимании термодинамики черных дыр через голографический принцип. Исследования продолжают открывать фундаментальные аспекты нашей Вселенной.",
          bullets: [],
          stats: [],
          images: ["https://images.unsplash.com/photo-1446776811953-b23d57bd21aa?q=80&w=1280&h=720&fit=crop"],
          properties: {
            companyName: "РОССИЙСКАЯ АКАДЕМИЯ НАУК",
            logoUrl: "https://presenton-public.s3.ap-southeast-1.amazonaws.com/static/icons/bold/fediverse-logo-bold.svg"
          }
        }
      ]
    };
  } else {
    // -------------------------------------------------------------
    // 1. Midnight Glass (Indigo Neon, Rubik Cyrillic) - Default
    // -------------------------------------------------------------
    presentation = {
      id: "quantum-glass",
      title: "Квантовый Интернет: Архитектура Будущего",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      data: null,
      file: "presentation.pptx",
      n_slides: 6,
      prompt: "Будущее коммуникаций и квантовый интернет",
      summary: "Потрясающая презентация в стиле Midnight Glass о квантовых сетях, запутанности, QKD и дорожной карте развития.",
      theme: {
        curated_palette: "midnight_glass"
      },
      titles: ["Обложка", "Технологии", "Эффективность", "Философия", "Дорожная Карта", "Заключение"],
      user_id: "user_glass",
      vector_store: null,
      thumbnail: "",
      slides: [
        {
          index: 0,
          type: "title",
          title: "КВАНТОВЫЙ ИНТЕРНЕТ",
          content: "Новая эра абсолютной безопасности, мгновенной передачи данных и квантовой запутанности в глобальном масштабе.",
          bullets: [],
          stats: [],
          images: ["https://images.unsplash.com/photo-1507668077129-56e32842fceb?q=80&w=1280&h=720&fit=crop"],
          properties: {
            companyName: "COSMO ARTIST LABS",
            logoUrl: "https://presenton-public.s3.ap-southeast-1.amazonaws.com/static/icons/bold/fediverse-logo-bold.svg"
          }
        },
        {
          index: 1,
          type: "bullets",
          title: "Ключевые Технологии Сети будущего",
          content: "Фундаментальные физические принципы, обеспечивающие передачу квантовых данных на макроуровне.",
          bullets: [
            "Квантовая запутанность: Мгновенная синхронизация состояний частиц на любых расстояниях во Вселенной.",
            "Распределение ключей (QKD): Абсолютная защита каналов от любого несанкционированного доступа на уровне законов физики.",
            "Квантовые повторители: Ретрансляция и преодоление естественного затухания сигналов в оптическом волокне.",
            "Стабильная память: Надежная буферизация кубитов без риска разрушения их когерентного состояния."
          ],
          stats: [],
          images: ["https://images.unsplash.com/photo-1635070041078-e363dbe005cb?q=80&w=1280&h=720&fit=crop"],
          icons: [
            "https://presenton-public.s3.ap-southeast-1.amazonaws.com/static/icons/bold/checks-bold.svg",
            "https://presenton-public.s3.ap-southeast-1.amazonaws.com/static/icons/bold/checks-bold.svg",
            "https://presenton-public.s3.ap-southeast-1.amazonaws.com/static/icons/bold/checks-bold.svg",
            "https://presenton-public.s3.ap-southeast-1.amazonaws.com/static/icons/bold/checks-bold.svg"
          ]
        },
        {
          index: 2,
          type: "stats",
          title: "Показатели Эффективности Сети",
          content: "Сравнение возможностей квантовой сети с классическими технологиями передачи данных.",
          bullets: [],
          stats: [
            { value: "100%", label: "Уровень физической защиты каналов" },
            { value: "< 1 мс", label: "Время квантовой синхронизации" },
            { value: "10^9", label: "Кубитов/с — скорость на узлах" },
            { value: "2030", label: "Глобальный коммерческий запуск" }
          ],
          images: ["https://images.unsplash.com/photo-1639762681485-074b7f938ba0?q=80&w=1280&h=720&fit=crop"]
        },
        {
          index: 3,
          type: "quote",
          title: "Философия Квантовых Коммуникаций",
          content: "«Квантовый интернет — это не просто ускорение привычных сетей. Это создание принципиально нового пространства безопасности, где попытка шпионажа физически разрушает перехватываемую информацию.»",
          bullets: [
            "Профессор Стивен Вайснер, Пионер квантовой криптографии и изобретатель сопряженного кодирования"
          ],
          stats: [],
          images: ["https://images.unsplash.com/photo-1451187580459-43490279c0fa?q=80&w=1280&h=720&fit=crop"]
        },
        {
          index: 4,
          type: "timeline",
          title: "Дорожная Карта Развития глобальной сети",
          content: "Основные этапы развертывания квантовой инфраструктуры на ближайшее десятилетие.",
          bullets: [
            "2024: Запуск локальных линий распределения квантовых ключей (QKD) банками и госкорпорациями.",
            "2026: Успешные испытания орбитальных квантовых ретрансляторов в открытом космосе.",
            "2028: Создание первых гетерогенных сетей (сочетание оптоволокна и спутниковых каналов).",
            "2030+: Формирование полноценной всемирной квантовой сети Quantum Web."
          ],
          stats: [],
          images: ["https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=1280&h=720&fit=crop"]
        },
        {
          index: 5,
          type: "closing",
          title: "Готовы ли вы к Квантовому Переходу?",
          content: "Внедрение квантовых коммуникаций потребует полной перестройки корпоративной безопасности. Начните аудит сетевой инфраструктуры вашей организации уже сегодня, плавно внедряя алгоритмы постквантового шифрования для надежной защиты ваших критических данных.",
          bullets: [],
          stats: [],
          images: ["https://images.unsplash.com/photo-1446776811953-b23d57bd21aa?q=80&w=1280&h=720&fit=crop"],
          properties: {
            companyName: "COSMO ARTIST LABS",
            logoUrl: "https://presenton-public.s3.ap-southeast-1.amazonaws.com/static/icons/bold/fediverse-logo-bold.svg"
          }
        }
      ]
    };
  }

  return NextResponse.json(presentation);
}
