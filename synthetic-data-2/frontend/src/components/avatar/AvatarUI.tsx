'use client'

import React from 'react'
import { PHOTO_POSES, UI_MODES, useAvatarConfiguratorStore } from '@/store/avatarConfiguratorStore'

const PosesBox = () => {
  const curPose = useAvatarConfiguratorStore((state) => state.pose)
  const setPose = useAvatarConfiguratorStore((state) => state.setPose)
  return (
    <div className="pointer-events-auto md:rounded-t-lg bg-gradient-to-br from-black/30 to-indigo-900/20 backdrop-blur-sm drop-shadow-md flex p-6 gap-3 overflow-x-auto noscrollbar">
      {Object.keys(PHOTO_POSES).map((pose) => (
        <button
          key={pose}
          className={`transition-colors duration-200 font-medium flex-shrink-0 border-b ${
            curPose === PHOTO_POSES[pose as keyof typeof PHOTO_POSES]
              ? "text-white shadow-purple-100 border-b-white"
              : "text-gray-200 hover:text-gray-100 border-b-transparent"
          }`}
          onClick={() => setPose(PHOTO_POSES[pose as keyof typeof PHOTO_POSES])}
        >
          {pose}
        </button>
      ))}
    </div>
  )
}

const AssetsBox = () => {
  const {
    categories,
    currentCategory,
    setCurrentCategory,
    changeAsset,
    customization,
    lockedGroups,
  } = useAvatarConfiguratorStore()

  return (
    <div className="md:rounded-t-lg bg-gradient-to-br from-black/30 to-indigo-900/20 backdrop-blur-sm drop-shadow-md flex flex-col py-6 gap-3 overflow-hidden">
      <div className="flex items-center gap-8 pointer-events-auto noscrollbar overflow-x-auto px-6 pb-2">
        {categories.map((category) => (
          <button
            key={category.id}
            onClick={() => setCurrentCategory(category)}
            className={`transition-colors duration-200 font-medium flex-shrink-0 border-b ${
              currentCategory?.name === category.name
                ? "text-white shadow-purple-100 border-b-white"
                : "text-gray-200 hover:text-gray-100 border-b-transparent"
            }`}
          >
            {category.name}
          </button>
        ))}
      </div>
      {lockedGroups[currentCategory?.name] && (
        <p className="text-red-400 px-6">
          Asset is hidden by{" "}
          {lockedGroups[currentCategory.name]
            .map((asset: any) => `${asset.name} (${asset.categoryName})`)
            .join(", ")}
        </p>
      )}
      <div className="flex gap-2 overflow-x-auto noscrollbar px-6">
        {currentCategory?.removable && (
          <button
            onClick={() => changeAsset(currentCategory.name, null)}
            className={`w-20 h-20 flex-shrink-0 rounded-xl overflow-hidden pointer-events-auto hover:opacity-100 transition-all border-2 duration-300
              bg-gradient-to-tr
              ${
                !customization[currentCategory.name]?.asset
                  ? "border-white from-white/20 to-white/30"
                  : "from-black/70 to-black/20 border-black"
              }`}
          >
            <div className="w-full h-full flex items-center justify-center bg-black/40 text-white">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
                className="size-8"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M6 18 18 6M6 6l12 12"
                />
              </svg>
            </div>
          </button>
        )}
        {currentCategory?.assets.map((asset: any) => (
          <button
            key={asset.thumbnail}
            onClick={() => changeAsset(currentCategory.name, asset)}
            className={`w-20 h-20 flex-shrink-0 rounded-xl overflow-hidden pointer-events-auto hover:opacity-100 transition-all border-2 duration-300
              bg-gradient-to-tr
              ${
                customization[currentCategory.name]?.asset?.id === asset.id
                  ? "border-white from-white/20 to-white/30"
                  : "from-black/70 to-black/20 border-black"
              }`}
          >
            <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-blue-500 to-purple-600 text-white text-xs font-medium">
              {asset.name}
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}

const RandomizeButton = () => {
  const randomize = useAvatarConfiguratorStore((state) => state.randomize)
  return (
    <button
      className="rounded-lg bg-indigo-500 hover:bg-indigo-600 transition-colors duration-300 text-white font-medium px-4 py-3 pointer-events-auto drop-shadow-md"
      onClick={randomize}
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        strokeWidth={1.5}
        stroke="currentColor"
        className="size-6"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M19.5 12c0-1.232-.046-2.453-.138-3.662a4.006 4.006 0 0 0-3.7-3.7 48.678 48.678 0 0 0-7.324 0 4.006 4.006 0 0 0-3.7 3.7c-.017.22-.032.441-.046.662M19.5 12l3-3m-3 3-3-3m-12 3c0 1.232.046 2.453.138 3.662a4.006 4.006 0 0 0 3.7 3.7 48.656 48.656 0 0 0 7.324 0 4.006 4.006 0 0 0 3.7-3.7c.017-.22.032-.441.046-.662M4.5 12l3 3m-3-3-3 3"
        />
      </svg>
    </button>
  )
}

const ScreenshotButton = () => {
  const screenshot = useAvatarConfiguratorStore((state) => state.screenshot)
  return (
    <button
      className="rounded-lg bg-indigo-500 hover:bg-indigo-600 transition-colors duration-300 text-white font-medium px-4 py-3 pointer-events-auto drop-shadow-md"
      onClick={screenshot}
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        strokeWidth={1.5}
        stroke="currentColor"
        className="size-6"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M6.827 6.175A2.31 2.31 0 0 1 5.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 0 0-1.134-.175 2.31 2.31 0 0 1-1.64-1.055l-.822-1.316a2.192 2.192 0 0 0-1.736-1.039 48.774 48.774 0 0 0-5.232 0 2.192 2.192 0 0 0-1.736 1.039l-.821 1.316Z"
        />
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M16.5 12.75a4.5 4.5 0 1 1-9 0 4.5 4.5 0 0 1 9 0ZM18.75 10.5h.008v.008h-.008V10.5Z"
        />
      </svg>
    </button>
  )
}

const DownloadButton = () => {
  const download = useAvatarConfiguratorStore((state) => state.download)
  return (
    <button
      className="rounded-lg bg-indigo-500 hover:bg-indigo-600 transition-colors duration-300 text-white font-medium px-4 py-3 pointer-events-auto drop-shadow-md"
      onClick={download}
    >
      Download
    </button>
  )
}

const ProgressBar = () => {
  const { categories, currentCategory } = useAvatarConfiguratorStore()
  const customization = useAvatarConfiguratorStore((state) => state.customization)
  
  const getCompletionStatus = (category: any) => {
    return customization[category.name]?.asset !== null
  }
  
  return (
    <div className="w-full mb-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-gray-300">Configuration Progress</span>
        <span className="text-sm text-gray-300">
          {categories.filter(cat => getCompletionStatus(cat)).length}/{categories.length}
        </span>
      </div>
      <div className="flex gap-1">
        {categories.map((category, index) => (
          <div
            key={category.id}
            className={`flex-1 h-2 rounded-full transition-all duration-300 ${
              getCompletionStatus(category)
                ? "bg-green-500"
                : currentCategory?.name === category.name
                ? "bg-blue-500"
                : "bg-gray-600"
            }`}
          />
        ))}
      </div>
    </div>
  )
}

const CategoryNavigation = () => {
  const { categories, currentCategory, setCurrentCategory } = useAvatarConfiguratorStore()
  
  const currentIndex = categories.findIndex(cat => cat.name === currentCategory?.name)
  
  const goToPrevious = () => {
    if (currentIndex > 0) {
      setCurrentCategory(categories[currentIndex - 1])
    }
  }
  
  const goToNext = () => {
    if (currentIndex < categories.length - 1) {
      setCurrentCategory(categories[currentIndex + 1])
    }
  }
  
  return (
    <div className="flex items-center justify-between mb-4">
      <button
        onClick={goToPrevious}
        disabled={currentIndex <= 0}
        className={`p-2 rounded-lg transition-colors duration-200 ${
          currentIndex <= 0
            ? "text-gray-500 cursor-not-allowed"
            : "text-white hover:bg-white/10 pointer-events-auto"
        }`}
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
      </button>
      
      <h3 className="text-lg font-medium text-white text-center flex-1">
        {currentCategory?.name || "Select Category"}
      </h3>
      
      <button
        onClick={goToNext}
        disabled={currentIndex >= categories.length - 1}
        className={`p-2 rounded-lg transition-colors duration-200 ${
          currentIndex >= categories.length - 1
            ? "text-gray-500 cursor-not-allowed"
            : "text-white hover:bg-white/10 pointer-events-auto"
        }`}
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </button>
    </div>
  )
}

const ColorPicker = () => {
  const updateColor = useAvatarConfiguratorStore((state) => state.updateColor)
  const currentCategory = useAvatarConfiguratorStore((state) => state.currentCategory)
  const customization = useAvatarConfiguratorStore((state) => state.customization)
  const { changeAsset } = useAvatarConfiguratorStore()

  const handleColorChange = (color: string) => {
    updateColor(color)
  }

  if (!customization[currentCategory?.name]?.asset) {
    return null
  }
  
  return (
    <div className="pointer-events-auto relative flex gap-2 max-w-full overflow-x-auto backdrop-blur-sm py-2 drop-shadow-md noscrollbar px-2 md:px-0">
      {currentCategory?.colorPalette?.colors.map((color: string, index: number) => (
        <button
          key={`${index}-${color}`}
          className={`w-10 h-10 p-1.5 drop-shadow-md bg-black/20 shrink-0 rounded-lg overflow-hidden transition-all duration-300 border-2
             ${
               customization[currentCategory.name]?.color === color
                 ? "border-white"
                 : "border-transparent"
             }
          `}
          onClick={() => handleColorChange(color)}
        >
          <div
            className="w-full h-full rounded-md"
            style={{ backgroundColor: color }}
          />
        </button>
      ))}
    </div>
  )
}

const ConfigurationPanel = () => {
  const currentCategory = useAvatarConfiguratorStore((state) => state.currentCategory)
  const customization = useAvatarConfiguratorStore((state) => state.customization)
  const mode = useAvatarConfiguratorStore((state) => state.mode)
  const setMode = useAvatarConfiguratorStore((state) => state.setMode)
  const { changeAsset } = useAvatarConfiguratorStore()
  
  return (
    <div className="w-80 h-full flex flex-col">
      {/* Progress Bar */}
      <div className="p-4">
        <ProgressBar />
      </div>
      
      {/* Configuration Card */}
      <div className="flex-1 bg-gradient-to-br from-black/40 to-indigo-900/30 backdrop-blur-sm rounded-lg m-4 flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-white/10">
          <h2 className="text-xl font-semibold text-white mb-4">Persona Traits</h2>
          <CategoryNavigation />
        </div>
        
        {/* Content Area */}
        <div className="flex-1 p-4 overflow-y-auto">
          {mode === UI_MODES.CUSTOMIZE && (
            <>
              {currentCategory?.colorPalette &&
                customization[currentCategory.name] && (
                <div className="mb-4">
                  <ColorPicker />
                </div>
              )}
              <div className="space-y-3">
                {currentCategory?.removable && (
                  <button
                    onClick={() => changeAsset(currentCategory.name, null)}
                    className={`w-full h-16 rounded-lg overflow-hidden pointer-events-auto hover:opacity-100 transition-all border-2 duration-300
                      bg-gradient-to-tr flex items-center justify-center
                      ${
                        !customization[currentCategory.name]?.asset
                          ? "border-white from-white/20 to-white/30"
                          : "from-black/70 to-black/20 border-black"
                      }`}
                  >
                    <div className="flex items-center justify-center bg-black/40 text-white">
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                        strokeWidth={1.5}
                        stroke="currentColor"
                        className="w-6 h-6 mr-2"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M6 18 18 6M6 6l12 12"
                        />
                      </svg>
                      Remove
                    </div>
                  </button>
                )}
                {currentCategory?.assets.map((asset: any) => (
                  <button
                    key={asset.thumbnail}
                    onClick={() => changeAsset(currentCategory.name, asset)}
                    className={`w-full h-16 rounded-lg overflow-hidden pointer-events-auto hover:opacity-100 transition-all border-2 duration-300
                      bg-gradient-to-tr flex items-center justify-center
                      ${
                        customization[currentCategory.name]?.asset?.id === asset.id
                          ? "border-white from-white/20 to-white/30"
                          : "from-black/70 to-black/20 border-black"
                      }`}
                  >
                    <div className="text-white text-sm font-medium">
                      {asset.name}
                    </div>
                  </button>
                ))}
              </div>
            </>
          )}
          {mode === UI_MODES.PHOTO && <PosesBox />}
        </div>
        
        {/* Action Buttons */}
        <div className="p-4 border-t border-white/10 space-y-2">
          <div className="flex gap-2">
            <RandomizeButton />
            <ScreenshotButton />
            <DownloadButton />
          </div>
          <button
            className="w-full pointer-events-auto p-3 text-white transition-colors duration-200 font-medium bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 rounded-lg shadow-lg"
            onClick={() => {
              setMode(mode === UI_MODES.CUSTOMIZE ? UI_MODES.PHOTO : UI_MODES.CUSTOMIZE)
            }}
          >
            {mode === UI_MODES.CUSTOMIZE ? 'Switch to Photo Mode' : 'Switch to Customize Mode'}
          </button>
        </div>
      </div>
    </div>
  )
}

export const AvatarUI = () => {
  const loading = useAvatarConfiguratorStore((state) => state.loading)
  
  return (
    <main className="pointer-events-none fixed z-10 inset-0 select-none">
      <div
        className={`absolute inset-0 bg-black z-10 pointer-events-none flex items-center justify-center transition-opacity duration-1000 ${
          loading ? "opacity-100" : "opacity-0"
        }`}
      >
        <div className="w-40 h-40 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full animate-pulse flex items-center justify-center">
          <span className="text-white text-2xl font-bold">Loading...</span>
        </div>
      </div>
      
      {/* Main Layout: Avatar on left, Configuration panel on right */}
      <div className="h-full flex">
        {/* Avatar Area (takes remaining space) */}
        <div className="flex-1" />
        
        {/* Configuration Panel (fixed width on right) */}
        <ConfigurationPanel />
      </div>
    </main>
  )
}

export { PosesBox, AssetsBox, RandomizeButton, ScreenshotButton, DownloadButton, ProgressBar, CategoryNavigation, ColorPicker, ConfigurationPanel }