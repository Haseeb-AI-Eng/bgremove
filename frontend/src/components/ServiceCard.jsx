import React from 'react';
import { Link } from 'react-router-dom';
import { FaArrowRight } from 'react-icons/fa';

const ServiceCard = ({ service, onClick }) => {
  const handleClick = (e) => {
    if (service.isImageEditor && onClick) {
      e.preventDefault();
      onClick();
    }
  };

  return (
    <div className="service-card group">
      <div className="service-card-inner">
        <div className="card-shine"></div>
        
        {/* Image header with gradient overlay */}
        <div className="relative h-44 overflow-hidden reflect-effect">
          {service.image ? (
            <>
              <img
                src={service.image}
                alt={service.title}
                className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110"
              />
              <div className={`absolute inset-0 bg-gradient-to-t ${service.color} opacity-60 mix-blend-multiply`}></div>
              <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent"></div>
            </>
          ) : (
            <div className={`h-full w-full flex items-center justify-center bg-gradient-to-br ${service.color}`}>
              <div className="text-white transform transition-transform duration-500 group-hover:scale-125">
                {service.icon}
              </div>
            </div>
          )}
          
          {/* Floating Icon Badge */}
          <div className="absolute top-4 right-4 w-10 h-10 rounded-full bg-white/10 backdrop-blur-md border border-white/20 flex items-center justify-center text-white shadow-lg transform -translate-y-2 opacity-0 group-hover:translate-y-0 group-hover:opacity-100 transition-all duration-300">
            {service.icon}
          </div>

          <div className="absolute bottom-4 left-5 right-5">
            <h3 className="text-lg font-bold text-white leading-tight drop-shadow-md">
              {service.title}
            </h3>
          </div>
        </div>

        <div className="p-6 flex-grow flex flex-col bg-white">
          <p className="text-gray-500 text-sm leading-relaxed mb-6 flex-grow">
            {service.description}
          </p>
          
          <div className="flex items-center justify-between">
            {service.isImageEditor ? (
              <button
                onClick={handleClick}
                className="btn-premium inline-flex items-center justify-center px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-xl shadow-lg shadow-indigo-200 transition-all active:scale-95"
              >
                Open Editor
                <FaArrowRight className="ml-2 text-xs transition-transform group-hover:translate-x-1" />
              </button>
            ) : (
              <Link
                to={service.path}
                className="btn-premium inline-flex items-center justify-center px-5 py-2.5 bg-slate-900 hover:bg-slate-800 text-white text-sm font-semibold rounded-xl shadow-lg shadow-slate-200 transition-all active:scale-95"
              >
                Try it Free
                <FaArrowRight className="ml-2 text-xs transition-transform group-hover:translate-x-1" />
              </Link>
            )}
            
            <span className="text-[10px] font-bold text-gray-300 uppercase tracking-widest group-hover:text-indigo-400 transition-colors">
              AI Powered
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ServiceCard;