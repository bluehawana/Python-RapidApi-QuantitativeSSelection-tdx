export default function Home() {
  return (
    <div className="space-y-6">
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">
          Formula Builder
        </h2>
        <p className="text-gray-500">
          Create custom screening formulas for convertible bonds.
        </p>
        {/* Formula Builder component will be added here */}
      </div>

      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">
          Screening Results
        </h2>
        <p className="text-gray-500">
          Results will appear here after executing a formula.
        </p>
        {/* Results Table component will be added here */}
      </div>
    </div>
  );
}
