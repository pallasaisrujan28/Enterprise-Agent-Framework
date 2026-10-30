/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    optimizePackageImports: ['lucide-react', '@radix-ui/react-icons', 'framer-motion', '@react-three/fiber', '@react-three/drei'],
    optimizeCss: true,
    webpackBuildWorker: true,
  },
  turbopack: {
    rules: {
      '*.svg': {
        loaders: ['@svgr/webpack'],
        as: '*.js',
      },
    },
  },
  images: {
    domains: ['localhost'],
    formats: ['image/webp', 'image/avif'],
  },
  compress: true,
  modularizeImports: {
    'lucide-react': {
      transform: 'lucide-react/dist/esm/icons/{{kebabCase member}}',
      preventFullImport: true,
    },
  },
  output: 'standalone',
  webpack: (config: any, { dev, isServer }: { dev: boolean; isServer: boolean }) => {
    // Optimize bundle splitting for better performance
    if (!dev && !isServer) {
      config.optimization.splitChunks = {
        chunks: 'all',
        cacheGroups: {
          vendor: {
            test: /[\/]node_modules[\/]/,
            name: 'vendors',
            chunks: 'all',
          },
          three: {
            test: /[\/]node_modules[\/](three|@react-three)[\/]/,
            name: 'three',
            chunks: 'all',
            priority: 10,
          },
          ui: {
            test: /[\/]node_modules[\/](@radix-ui|@headlessui)[\/]/,
            name: 'ui',
            chunks: 'all',
            priority: 10,
          },
        },
      }
    }
    return config
  },
};

export default nextConfig;
