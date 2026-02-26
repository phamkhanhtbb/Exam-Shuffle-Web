import {
  Shuffle,
  FileText,
  Download,
  Zap,
  Shield,
  Clock,
  Upload,
  Sparkles,
  CheckCircle,
  ArrowRight,
  GraduationCap,
} from "lucide-react";

const APP_URL = "https://app.trondeonline.me";

export default function Home() {
  return (
    <>
      {/* JSON-LD Structured Data */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "SoftwareApplication",
            name: "ExamShuffling - Trộn đề thi trắc nghiệm",
            description:
              "Công cụ trộn đề thi trắc nghiệm online miễn phí. Hỗ trợ đảo câu hỏi, đảo đáp án, xuất file Word tự động cho giáo viên.",
            url: "https://trondeonline.me",
            applicationCategory: "EducationalApplication",
            operatingSystem: "Web Browser",
            offers: {
              "@type": "Offer",
              price: "0",
              priceCurrency: "VND",
            },
            author: {
              "@type": "Person",
              name: "David Khanh",
            },
            inLanguage: "vi",
            aggregateRating: {
              "@type": "AggregateRating",
              ratingValue: "4.8",
              ratingCount: "150",
            },
          }),
        }}
      />

      <div className="min-h-screen">
        {/* =============================
            NAVIGATION
            ============================= */}
        <nav className="fixed top-0 left-0 right-0 z-50 animate-fade-in-down">
          <div className="glass mx-auto max-w-7xl mt-4 mx-4 sm:mx-6 lg:mx-auto rounded-2xl px-6 py-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-2xl">🎓</span>
              <span className="text-lg font-bold text-white tracking-tight">
                ExamShuffling
              </span>
            </div>
            <a
              href={APP_URL}
              className="inline-flex items-center gap-2 bg-white/15 hover:bg-white/25 text-white text-sm font-semibold px-5 py-2.5 rounded-xl transition-all duration-300 hover:scale-105"
            >
              Bắt đầu ngay
              <ArrowRight className="w-4 h-4" />
            </a>
          </div>
        </nav>

        {/* =============================
            HERO SECTION
            ============================= */}
        <section
          className="relative min-h-screen flex items-center justify-center overflow-hidden"
          style={{
            background:
              "linear-gradient(135deg, #667eea 0%, #764ba2 50%, #6366f1 100%)",
          }}
        >
          {/* Background decorative elements */}
          <div className="absolute inset-0 overflow-hidden pointer-events-none">
            <div className="absolute top-20 left-10 w-72 h-72 bg-white/5 rounded-full blur-3xl animate-float" />
            <div className="absolute bottom-20 right-10 w-96 h-96 bg-purple-300/10 rounded-full blur-3xl animate-float delay-300" />
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-indigo-400/5 rounded-full blur-3xl" />
          </div>

          <div className="relative z-10 max-w-5xl mx-auto px-6 text-center pt-24 pb-16">
            {/* Badge */}
            <div className="animate-fade-in-up inline-flex items-center gap-2 bg-white/10 rounded-full px-4 py-2 mb-8 border border-white/20">
              <Sparkles className="w-4 h-4 text-yellow-300" />
              <span className="text-sm text-white/90 font-medium">
                Miễn phí 100% — Không cần đăng ký
              </span>
            </div>

            {/* Main heading */}
            <h1 className="animate-fade-in-up delay-100 text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-extrabold text-white leading-tight tracking-tight mb-6">
              Trộn đề thi trắc nghiệm
              <br />
              <span className="bg-gradient-to-r from-yellow-200 via-pink-200 to-purple-200 bg-clip-text text-transparent">
                chỉ trong vài giây
              </span>
            </h1>

            {/* Subtitle */}
            <p className="animate-fade-in-up delay-200 text-lg sm:text-xl text-indigo-100 max-w-2xl mx-auto mb-10 leading-relaxed">
              Upload file Word → Đảo câu hỏi & đáp án tự động → Tải về nhiều
              mã đề khác nhau. Công cụ đắc lực cho giáo viên Việt Nam.
            </p>

            {/* CTA Buttons */}
            <div className="animate-fade-in-up delay-300 flex flex-col sm:flex-row items-center justify-center gap-4">
              <a
                href={APP_URL}
                className="group inline-flex items-center gap-3 bg-white text-indigo-700 font-bold text-lg px-8 py-4 rounded-2xl shadow-xl hover:shadow-2xl transition-all duration-300 hover:scale-105 animate-pulse-glow"
              >
                <Upload className="w-5 h-5" />
                Bắt đầu trộn đề ngay
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </a>
              <a
                href="#features"
                className="inline-flex items-center gap-2 text-white/80 hover:text-white font-medium text-base px-6 py-4 rounded-2xl border border-white/20 hover:bg-white/10 transition-all duration-300"
              >
                Tìm hiểu thêm
              </a>
            </div>

            {/* Stats */}
            <div className="animate-fade-in-up delay-500 grid grid-cols-3 gap-6 mt-16 max-w-lg mx-auto">
              {[
                { value: "100%", label: "Miễn phí" },
                { value: "~5s", label: "Thời gian xử lý" },
                { value: "∞", label: "Không giới hạn" },
              ].map((stat) => (
                <div key={stat.label} className="text-center">
                  <p className="text-2xl sm:text-3xl font-extrabold text-white">
                    {stat.value}
                  </p>
                  <p className="text-xs sm:text-sm text-indigo-200 mt-1">
                    {stat.label}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Wave separator */}
          <div className="absolute bottom-0 left-0 right-0">
            <svg
              viewBox="0 0 1440 120"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              className="w-full"
            >
              <path
                d="M0 120L60 105C120 90 240 60 360 45C480 30 600 30 720 37.5C840 45 960 60 1080 67.5C1200 75 1320 75 1380 75L1440 75V120H1380C1320 120 1200 120 1080 120C960 120 840 120 720 120C600 120 480 120 360 120C240 120 120 120 60 120H0Z"
                fill="#f8fafc"
              />
            </svg>
          </div>
        </section>

        {/* =============================
            FEATURES SECTION
            ============================= */}
        <section id="features" className="py-20 sm:py-28 bg-slate-50">
          <div className="max-w-6xl mx-auto px-6">
            {/* Section header */}
            <div className="text-center mb-16">
              <span className="inline-flex items-center gap-2 bg-indigo-50 text-indigo-700 text-sm font-semibold px-4 py-2 rounded-full mb-4">
                <Zap className="w-4 h-4" />
                Tính năng nổi bật
              </span>
              <h2 className="text-3xl sm:text-4xl font-extrabold text-gray-900 tracking-tight">
                Mọi thứ bạn cần để{" "}
                <span className="gradient-text">tạo đề thi</span>
              </h2>
              <p className="text-gray-500 mt-4 max-w-xl mx-auto text-lg">
                Thiết kế dành riêng cho giáo viên Việt Nam — đơn giản, nhanh
                chóng, và hoàn toàn tự động.
              </p>
            </div>

            {/* Feature cards */}
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {[
                {
                  icon: Shuffle,
                  title: "Đảo câu hỏi thông minh",
                  desc: "Tự động xáo trộn thứ tự câu hỏi để tạo ra nhiều mã đề khác nhau từ cùng một ngân hàng câu hỏi.",
                  color: "from-indigo-500 to-blue-500",
                  bgColor: "bg-indigo-50",
                  iconColor: "text-indigo-600",
                },
                {
                  icon: CheckCircle,
                  title: "Đảo đáp án tự động",
                  desc: "Sắp xếp lại thứ tự các đáp án A, B, C, D cho mỗi câu hỏi, đảm bảo công bằng và chống gian lận.",
                  color: "from-purple-500 to-pink-500",
                  bgColor: "bg-purple-50",
                  iconColor: "text-purple-600",
                },
                {
                  icon: FileText,
                  title: "Xuất file Word hoàn chỉnh",
                  desc: "Tải về file .docx đẹp mắt với đầy đủ định dạng, header, đáp án, sẵn sàng in ấn ngay lập tức.",
                  color: "from-emerald-500 to-teal-500",
                  bgColor: "bg-emerald-50",
                  iconColor: "text-emerald-600",
                },
                {
                  icon: Zap,
                  title: "Xử lý siêu nhanh",
                  desc: "Engine xử lý trên cloud — trộn xong hàng chục mã đề chỉ trong vài giây, không phải chờ đợi.",
                  color: "from-amber-500 to-orange-500",
                  bgColor: "bg-amber-50",
                  iconColor: "text-amber-600",
                },
                {
                  icon: Shield,
                  title: "Bảo mật tuyệt đối",
                  desc: "File của bạn được xử lý an toàn trên server và tự động xóa sau khi hoàn thành. Không lưu trữ lâu dài.",
                  color: "from-cyan-500 to-blue-500",
                  bgColor: "bg-cyan-50",
                  iconColor: "text-cyan-600",
                },
                {
                  icon: Clock,
                  title: "Tiết kiệm hàng giờ",
                  desc: "Việc trộn đề thủ công tốn hàng giờ đồng hồ. Với ExamShuffling, chỉ cần upload và đợi kết quả.",
                  color: "from-rose-500 to-red-500",
                  bgColor: "bg-rose-50",
                  iconColor: "text-rose-600",
                },
              ].map((feature) => (
                <div
                  key={feature.title}
                  className="group glass-card rounded-2xl p-6 hover:shadow-xl transition-all duration-300 hover:-translate-y-1"
                >
                  <div
                    className={`w-12 h-12 ${feature.bgColor} rounded-xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform`}
                  >
                    <feature.icon className={`w-6 h-6 ${feature.iconColor}`} />
                  </div>
                  <h3 className="font-bold text-gray-900 text-lg mb-2">
                    {feature.title}
                  </h3>
                  <p className="text-gray-500 text-sm leading-relaxed">
                    {feature.desc}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* =============================
            HOW IT WORKS SECTION
            ============================= */}
        <section className="py-20 sm:py-28 bg-white">
          <div className="max-w-5xl mx-auto px-6">
            {/* Section header */}
            <div className="text-center mb-16">
              <span className="inline-flex items-center gap-2 bg-purple-50 text-purple-700 text-sm font-semibold px-4 py-2 rounded-full mb-4">
                <GraduationCap className="w-4 h-4" />
                Hướng dẫn sử dụng
              </span>
              <h2 className="text-3xl sm:text-4xl font-extrabold text-gray-900 tracking-tight">
                Chỉ <span className="gradient-text">3 bước</span> đơn giản
              </h2>
              <p className="text-gray-500 mt-4 max-w-xl mx-auto text-lg">
                Không cần cài đặt phần mềm. Không cần đăng ký tài khoản. Mọi
                thứ diễn ra trên trình duyệt web.
              </p>
            </div>

            {/* Steps */}
            <div className="grid md:grid-cols-3 gap-8 relative">
              {/* Connector line (desktop only) */}
              <div className="hidden md:block absolute top-16 left-[16.66%] right-[16.66%] h-0.5 bg-gradient-to-r from-indigo-200 via-purple-200 to-pink-200" />

              {[
                {
                  step: "01",
                  icon: Upload,
                  title: "Upload file Word",
                  desc: "Kéo thả hoặc chọn file .docx chứa đề thi gốc của bạn. Hệ thống sẽ tự động phân tích cấu trúc câu hỏi.",
                  gradient: "from-indigo-500 to-blue-500",
                },
                {
                  step: "02",
                  icon: Sparkles,
                  title: "Xem trước & chỉnh sửa",
                  desc: "Kiểm tra nội dung, đánh dấu đáp án đúng, chỉnh sửa nếu cần. Editor trực quan giúp bạn thao tác nhanh chóng.",
                  gradient: "from-purple-500 to-pink-500",
                },
                {
                  step: "03",
                  icon: Download,
                  title: "Tải về ngay",
                  desc: "Chọn số lượng mã đề cần tạo, nhấn xử lý và tải file Word hoàn chỉnh về máy. Sẵn sàng in ấn!",
                  gradient: "from-emerald-500 to-teal-500",
                },
              ].map((item) => (
                <div key={item.step} className="relative text-center group">
                  {/* Step number circle */}
                  <div className="relative inline-flex items-center justify-center mb-6">
                    <div
                      className={`w-16 h-16 rounded-2xl bg-gradient-to-br ${item.gradient} flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform duration-300`}
                    >
                      <item.icon className="w-7 h-7 text-white" />
                    </div>
                    <span className="absolute -top-2 -right-2 w-7 h-7 bg-white border-2 border-gray-100 rounded-full text-xs font-bold text-gray-600 flex items-center justify-center shadow-sm">
                      {item.step}
                    </span>
                  </div>

                  <h3 className="font-bold text-gray-900 text-xl mb-3">
                    {item.title}
                  </h3>
                  <p className="text-gray-500 text-sm leading-relaxed max-w-xs mx-auto">
                    {item.desc}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* =============================
            CTA SECTION
            ============================= */}
        <section className="py-20 sm:py-28">
          <div className="max-w-4xl mx-auto px-6">
            <div
              className="relative rounded-3xl overflow-hidden p-10 sm:p-16 text-center"
              style={{
                background:
                  "linear-gradient(135deg, #667eea 0%, #764ba2 50%, #6366f1 100%)",
              }}
            >
              {/* Decorative blobs */}
              <div className="absolute top-0 left-0 w-64 h-64 bg-white/5 rounded-full blur-3xl -translate-x-1/2 -translate-y-1/2" />
              <div className="absolute bottom-0 right-0 w-80 h-80 bg-purple-300/10 rounded-full blur-3xl translate-x-1/3 translate-y-1/3" />

              <div className="relative z-10">
                <span className="text-5xl mb-6 block">🚀</span>
                <h2 className="text-3xl sm:text-4xl font-extrabold text-white mb-4 tracking-tight">
                  Sẵn sàng trộn đề?
                </h2>
                <p className="text-indigo-100 text-lg max-w-lg mx-auto mb-8">
                  Hoàn toàn miễn phí. Không cần đăng ký. Bắt đầu trộn đề thi
                  ngay bây giờ và tiết kiệm hàng giờ soạn bài.
                </p>
                <a
                  href={APP_URL}
                  className="group inline-flex items-center gap-3 bg-white text-indigo-700 font-bold text-lg px-10 py-4 rounded-2xl shadow-xl hover:shadow-2xl transition-all duration-300 hover:scale-105"
                >
                  <Upload className="w-5 h-5" />
                  Mở công cụ trộn đề
                  <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                </a>
              </div>
            </div>
          </div>
        </section>

        {/* =============================
            FOOTER
            ============================= */}
        <footer className="bg-gray-900 py-12">
          <div className="max-w-6xl mx-auto px-6">
            <div className="flex flex-col md:flex-row items-center justify-between gap-6">
              {/* Logo */}
              <div className="flex items-center gap-2">
                <span className="text-2xl">🎓</span>
                <span className="text-lg font-bold text-white">
                  ExamShuffling
                </span>
              </div>

              {/* Links */}
              <div className="flex items-center gap-6 text-sm text-gray-400">
                <a
                  href={APP_URL}
                  className="hover:text-white transition-colors"
                >
                  Bắt đầu
                </a>
                <a
                  href="#features"
                  className="hover:text-white transition-colors"
                >
                  Tính năng
                </a>
                <a
                  href="mailto:phamkhanhtbb@gmail.com"
                  className="hover:text-white transition-colors"
                >
                  Liên hệ
                </a>
              </div>

              {/* Credits */}
              <p className="text-sm text-gray-500">
                © 2025 ExamShuffling. Phát triển bởi{" "}
                <span className="text-gray-400 font-medium">
                  David Khanh 👾
                </span>
              </p>
            </div>
          </div>
        </footer>
      </div>
    </>
  );
}
