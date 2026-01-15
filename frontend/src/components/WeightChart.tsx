import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler } from 'chart.js';
import { Line } from 'react-chartjs-2';
import type { ContextData } from '../types/schema';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

interface WeightChartProps {
    data: ContextData['runner']['weight_kg'];
}

export function WeightChart({ data }: WeightChartProps) {
    const history = data.history || [];
    
    const chartData = {
        labels: history.map(h => new Date(h.date).toLocaleDateString('en-AU', { month: 'short', day: 'numeric' })),
        datasets: [{
            label: 'Weight (kg)',
            data: history.map(h => h.weight),
            borderColor: '#f97316',
            backgroundColor: 'rgba(249, 115, 22, 0.1)',
            borderWidth: 2,
            fill: true,
            tension: 0.4,
            pointRadius: 3
        }]
    };

    const options = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { display: false }
        },
        scales: {
            y: {
                beginAtZero: false,
                grid: { display: false },
                ticks: { font: { size: 10 } }
            },
            x: {
                grid: { display: false },
                ticks: { font: { size: 10 } }
            }
        }
    };

    return <Line data={chartData} options={options} />;
}
