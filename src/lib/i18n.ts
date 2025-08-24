import { writable, derived } from 'svelte/store';

export type Language = 'en' | 'ru';

export const currentLanguage = writable<Language>('en');

// Translations object
export const translations = {
  en: {
    // App navigation
    app_title: 'RAG App',
    nav_rag: 'RAG',
    nav_rag_description: 'Document Retrieval',
    nav_finetune: 'Fine-tune',
    nav_finetune_description: 'Model Training',
    nav_playground: 'Playground', 
    nav_playground_description: 'Test Models',
    nav_monitor: 'Monitor',
    nav_monitor_description: 'System & Metrics',
    status_ready: 'Ready',
    
    // RAG Panel
    rag_title: 'RAG App',
    rag_subtitle: 'Retrieval-Augmented Generation Assistant',
    tab_chat: 'Chat',
    tab_documents: 'Documents',
    tab_search: 'Search',
    tab_rag_config: 'RAG Config',
    tab_rag_test: 'Test RAG',
    
    // Chat interface
    chat_placeholder: 'Ask me anything about your documents... e.g., "What are the key findings in the Q3 report?"',
    chat_send: 'Send',
    chat_clear: 'Clear Chat',
    chat_welcome_title: 'Welcome to your RAG Assistant! 👋',
    chat_welcome_desc: 'Ask questions about your uploaded documents and I\'ll help you find answers.',
    
    // Documents
    documents_upload: 'Upload Documents',
    documents_drop_zone: 'Drop your files here or click to select',
    documents_supported: 'Supported formats: PDF, TXT, MD, DOCX',
    documents_delete: 'Delete',
    documents_view: 'View',
    documents_no_docs: 'No documents uploaded yet',
    documents_library: 'Document Library',
    documents_upload_first: 'Upload your first document to get started.',
    documents_start_chatting: 'Upload some documents to start chatting with your knowledge base.',
    
    // Upload features
    instant_processing: 'Instant processing',
    secure_private: 'Secure & private',
    ai_powered_analysis: 'AI-powered analysis',
    
    // Chat suggestions
    summarize_topics: 'Summarize topics',
    key_insights: 'Key insights',
    important_dates: 'Important dates',
    
    // Search
    search_placeholder: 'Search in documents... e.g., "machine learning algorithms"',
    search_button: 'Search',
    search_no_results: 'No results found',
    search_documents: 'Search Documents',
    search_results: 'Search Results',
    
    // RAG Config
    config_title: 'RAG Configuration',
    config_subtitle: 'Configure your RAG pipeline settings',
    config_embedding_model: 'Embedding Model',
    config_mode: 'RAG Mode',
    config_chunk_size: 'Chunk Size',
    config_chunk_overlap: 'Chunk Overlap',
    config_top_k: 'Top K Results',
    config_similarity_threshold: 'Similarity Threshold',
    config_save: 'Save Configuration',
    config_reset: 'Reset to Defaults',
    
    // Test RAG
    test_title: 'RAG Testing',
    test_subtitle: 'Test your RAG configuration with sample queries',
    test_query_placeholder: 'Enter your test query... e.g., "Explain the methodology described in the research paper"',
    test_run: 'Run Test',
    test_results: 'Test Results',
    test_query_label: 'Test Query:',
    
    // Fine-tune Panel
    finetune_title: 'Advanced Fine-Tuning',
    finetune_subtitle: 'Professional model training with LoRA, QLoRA, and RAG optimization',
    finetune_config: 'Configuration',
    finetune_models: 'Models',
    finetune_logs: 'Training Logs',
    finetune_charts: 'Loss Charts',
    finetune_dataset: 'Training Dataset',
    finetune_model: 'Base Model',
    finetune_parameters: 'Training Parameters',
    finetune_start: 'Start Training',
    finetune_stop: 'Stop Training',
    finetune_progress: 'Training Progress',
    finetune_epochs: 'Epochs',
    finetune_learning_rate: 'Learning Rate',
    finetune_batch_size: 'Batch Size',
    finetune_basic_config: 'Basic Configuration',
    finetune_lora_config: 'LoRA & QLoRA Configuration',
    finetune_training_params: 'Training Parameters',
    finetune_rag_settings: 'RAG-Specific Settings',
    finetune_advanced_config: 'Advanced Configuration',
    finetune_models_manage: 'Manage your trained models and configurations',
    finetune_logs_monitor: 'Monitor your fine-tuning progress in real-time',
    finetune_charts_visualize: 'Visualize training loss and performance metrics',
    
    // Advanced Configuration
    advanced_config: 'Advanced Configuration',
    save_steps: 'Save Steps',
    eval_steps: 'Evaluation Steps',
    logging_steps: 'Logging Steps',
    dataloader_workers: 'DataLoader Workers',
    instruction_template: 'Instruction Template',
    training_summary: 'Training Summary',
    default_template: 'Default',
    
    // Playground Panel
    playground_title: 'Playground',
    playground_subtitle: 'Interactive model testing environment',
    playground_prompt: 'Enter your prompt here...',
    playground_prompt_placeholder: 'e.g., "Write a summary of the key findings in artificial intelligence research..."',
    playground_model_select: 'Select Model',
    playground_temperature: 'Temperature',
    playground_max_tokens: 'Max Tokens',
    playground_generate: 'Generate',
    playground_clear: 'Clear',
    playground_response: 'Model Response',
    
    // Monitor Panel
    monitor_title: 'Monitor',
    monitor_subtitle: 'Real-time system monitoring and analytics',
    monitor_overview: 'Overview',
    monitor_system: 'System',
    monitor_tokens: 'Tokens',
    monitor_metrics: 'Metrics',
    monitor_logs: 'Logs',
    monitor_cpu_usage: 'CPU Usage',
    monitor_memory_usage: 'Memory Usage',
    monitor_disk_usage: 'Disk Usage',
    monitor_network: 'Network',
    monitor_uptime: 'Uptime',
    monitor_requests: 'Requests',
    monitor_errors: 'Errors',
    
    // Common actions
    save: 'Save',
    cancel: 'Cancel',
    edit: 'Edit',
    delete: 'Delete',
    upload: 'Upload',
    download: 'Download',
    loading: 'Loading...',
    error: 'Error',
    success: 'Success',
    warning: 'Warning',
    info: 'Info'
  },
  ru: {
    // App navigation
    app_title: 'RAG Приложение',
    nav_rag: 'RAG',
    nav_rag_description: 'Поиск по документам',
    nav_finetune: 'Настройка',
    nav_finetune_description: 'Обучение модели',
    nav_playground: 'Песочница',
    nav_playground_description: 'Тестирование моделей',
    nav_monitor: 'Мониторинг',
    nav_monitor_description: 'Система и метрики',
    status_ready: 'Готов',
    
    // RAG Panel
    rag_title: 'RAG Приложение',
    rag_subtitle: 'Ассистент с дополненной генерацией',
    tab_chat: 'Чат',
    tab_documents: 'Документы',
    tab_search: 'Поиск',
    tab_rag_config: 'Настройки RAG',
    tab_rag_test: 'Тест RAG',
    
    // Chat interface
    chat_placeholder: 'Задайте любой вопрос о ваших документах... например: "Какие ключевые выводы в отчёте за 3 квартал?"',
    chat_send: 'Отправить',
    chat_clear: 'Очистить чат',
    chat_welcome_title: 'Добро пожаловать в ваш RAG ассистент! 👋',
    chat_welcome_desc: 'Задавайте вопросы о загруженных документах, и я помогу найти ответы.',
    
    // Documents
    documents_upload: 'Загрузить документы',
    documents_drop_zone: 'Перетащите файлы сюда или нажмите для выбора',
    documents_supported: 'Поддерживаемые форматы: PDF, TXT, MD, DOCX',
    documents_delete: 'Удалить',
    documents_view: 'Просмотр',
    documents_no_docs: 'Документы ещё не загружены',
    documents_library: 'Библиотека документов',
    documents_upload_first: 'Загрузите ваш первый документ для начала работы.',
    documents_start_chatting: 'Загрузите документы, чтобы начать общение с вашей базой знаний.',
    
    // Upload features
    instant_processing: 'Мгновенная обработка',
    secure_private: 'Безопасно и приватно',
    ai_powered_analysis: 'ИИ-анализ данных',
    
    // Chat suggestions
    summarize_topics: 'Обзор тем',
    key_insights: 'Ключевые выводы',
    important_dates: 'Важные даты',
    
    // Search
    search_placeholder: 'Поиск в документах... например: "алгоритмы машинного обучения"',
    search_button: 'Найти',
    search_no_results: 'Результаты не найдены',
    search_documents: 'Поиск документов',
    search_results: 'Результаты поиска',
    
    // RAG Config
    config_title: 'Конфигурация RAG',
    config_subtitle: 'Настройте параметры вашего RAG конвейера',
    config_embedding_model: 'Модель эмбеддингов',
    config_mode: 'Режим RAG',
    config_chunk_size: 'Размер блока',
    config_chunk_overlap: 'Перекрытие блоков',
    config_top_k: 'Топ K результатов',
    config_similarity_threshold: 'Порог схожести',
    config_save: 'Сохранить конфигурацию',
    config_reset: 'Сбросить к умолчанию',
    
    // Test RAG
    test_title: 'Тестирование RAG',
    test_subtitle: 'Протестируйте вашу конфигурацию RAG с примерами запросов',
    test_query_placeholder: 'Введите ваш тестовый запрос... например: "Объясните методологию, описанную в исследовательской работе"',
    test_run: 'Запустить тест',
    test_results: 'Результаты теста',
    test_query_label: 'Тестовый запрос:',
    
    // Fine-tune Panel
    finetune_title: 'Продвинутая настройка',
    finetune_subtitle: 'Профессиональное обучение моделей с LoRA, QLoRA и оптимизацией RAG',
    finetune_config: 'Конфигурация',
    finetune_models: 'Модели',
    finetune_logs: 'Логи обучения',
    finetune_charts: 'Графики потерь',
    finetune_dataset: 'Обучающий набор данных',
    finetune_model: 'Базовая модель',
    finetune_parameters: 'Параметры обучения',
    finetune_start: 'Начать обучение',
    finetune_stop: 'Остановить обучение',
    finetune_progress: 'Прогресс обучения',
    finetune_epochs: 'Эпохи',
    finetune_learning_rate: 'Скорость обучения',
    finetune_batch_size: 'Размер пакета',
    finetune_basic_config: 'Базовая конфигурация',
    finetune_lora_config: 'Конфигурация LoRA и QLoRA',
    finetune_training_params: 'Параметры обучения',
    finetune_rag_settings: 'Настройки RAG',
    finetune_advanced_config: 'Продвинутая конфигурация',
    finetune_models_manage: 'Управление обученными моделями и конфигурациями',
    finetune_logs_monitor: 'Мониторинг прогресса точной настройки в реальном времени',
    finetune_charts_visualize: 'Визуализация потерь обучения и метрик производительности',
    
    // Advanced Configuration
    advanced_config: 'Продвинутая конфигурация',
    save_steps: 'Шаги сохранения',
    eval_steps: 'Шаги оценки',
    logging_steps: 'Шаги логирования',
    dataloader_workers: 'Рабочие процессы DataLoader',
    instruction_template: 'Шаблон инструкций',
    training_summary: 'Сводка обучения',
    default_template: 'По умолчанию',
    
    // Playground Panel
    playground_title: 'Песочница',
    playground_subtitle: 'Интерактивная среда тестирования моделей',
    playground_prompt: 'Введите ваш запрос здесь...',
    playground_prompt_placeholder: 'например: "Напишите краткое изложение ключевых выводов в исследованиях искусственного интеллекта..."',
    playground_model_select: 'Выбрать модель',
    playground_temperature: 'Температура',
    playground_max_tokens: 'Макс. токенов',
    playground_generate: 'Генерировать',
    playground_clear: 'Очистить',
    playground_response: 'Ответ модели',
    
    // Monitor Panel
    monitor_title: 'Мониторинг',
    monitor_subtitle: 'Мониторинг системы и аналитика в реальном времени',
    monitor_overview: 'Обзор',
    monitor_system: 'Система',
    monitor_tokens: 'Токены',
    monitor_metrics: 'Метрики',
    monitor_logs: 'Логи',
    monitor_cpu_usage: 'Использование ЦП',
    monitor_memory_usage: 'Использование памяти',
    monitor_disk_usage: 'Использование диска',
    monitor_network: 'Сеть',
    monitor_uptime: 'Время работы',
    monitor_requests: 'Запросы',
    monitor_errors: 'Ошибки',
    
    // Common actions
    save: 'Сохранить',
    cancel: 'Отмена',
    edit: 'Редактировать',
    delete: 'Удалить',
    upload: 'Загрузить',
    download: 'Скачать',
    loading: 'Загрузка...',
    error: 'Ошибка',
    success: 'Успех',
    warning: 'Предупреждение',
    info: 'Информация'
  }
};

// Create a derived store for the current translations
export const t = derived(currentLanguage, ($currentLanguage) => translations[$currentLanguage]);

// Helper function to get translation
export function translate(key: keyof typeof translations.en): string {
  let currentTranslations: any;
  currentLanguage.subscribe(lang => {
    currentTranslations = translations[lang];
  })();
  return currentTranslations?.[key] || translations.en[key] || key;
}

// Initialize language from localStorage if available
if (typeof window !== 'undefined') {
  const stored = localStorage.getItem('language') as Language;
  if (stored && (stored === 'en' || stored === 'ru')) {
    currentLanguage.set(stored);
  }
  
  currentLanguage.subscribe((lang) => {
    localStorage.setItem('language', lang);
    document.documentElement.setAttribute('lang', lang);
  });
}
