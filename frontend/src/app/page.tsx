import Converter from "../components/Converter";

export default function Home() {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col font-sans">
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-5xl mx-auto px-6 h-16 flex items-center">
          <h1 className="text-xl font-bold text-gray-900 tracking-tight">
            Document to PDF
          </h1>
        </div>
      </header>

      <main className="flex-1 flex flex-col items-center justify-center p-6 sm:p-12">
        <div className="mb-10 text-center max-w-xl mx-auto">
          <h2 className="text-4xl font-extrabold text-gray-900 tracking-tight mb-4">
            Convert Documents to PDF
          </h2>
          <p className="text-lg text-gray-600">
            Fast, secure, and accurate conversion for your Word documents. Files are processed in memory and deleted after conversion.
          </p>
        </div>

        <Converter />
        
        <p className="mt-12 text-sm text-gray-400 max-w-sm text-center">
          Your files are processed securely and temporarily stored on our servers. They are automatically deleted after conversion.
        </p>
      </main>
    </div>
  );
}
